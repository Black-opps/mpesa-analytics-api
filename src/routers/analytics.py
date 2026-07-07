# src/routers/analytics.py - COMPLETE WITH ROUTER-LEVEL TIMING

import csv
import io
import logging
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session
from src.core.database import Transaction, get_db
from src.core.dependencies import get_current_tenant_id, get_current_user
from src.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def _detect_counterparty_type(name: str) -> str:
    """Detect counterparty type based on name patterns."""
    if not name:
        return "unknown"

    business_keywords = [
        "Ltd",
        "Limited",
        "Shop",
        "Mart",
        "Supermarket",
        "Restaurant",
        "Cafe",
        "Store",
        "Mall",
        "Hotel",
    ]
    utility_keywords = [
        "Safaricom",
        "KPLC",
        "Water",
        "Internet",
        "Bill",
        "Token",
        "Electricity",
        "Kenya Power",
    ]

    name_lower = name.lower()
    if any(k.lower() in name_lower for k in utility_keywords):
        return "utility"
    if any(k.lower() in name_lower for k in business_keywords):
        return "business"
    if name.startswith("07") and len(name) >= 10:
        return "person"
    if name.startswith("01") and len(name) >= 10:
        return "person"
    if name.startswith("+254") and len(name) >= 12:
        return "person"
    return "unknown"


def _format_currency(amount: float) -> str:
    """Format currency for display"""
    return f"KES {amount:,.2f}"


def _generate_excel_report(transactions: List[Dict], summary: Dict) -> bytes:
    """Generate Excel report from transactions and summary"""
    wb = openpyxl.Workbook()

    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Summary"

    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(
        start_color="1a5276", end_color="1a5276", fill_type="solid"
    )
    header_alignment = Alignment(horizontal="center", vertical="center")

    ws_summary.merge_cells("A1:D1")
    title_cell = ws_summary["A1"]
    title_cell.value = f"Financial Report - {datetime.now().strftime('%B %d, %Y')}"
    title_cell.font = Font(bold=True, size=16)
    title_cell.alignment = Alignment(horizontal="center")

    summary_data = [
        ("Metric", "Value"),
        ("Total Income", _format_currency(summary.get("money_in", 0))),
        ("Total Expenses", _format_currency(summary.get("money_out", 0))),
        ("Net Cash Flow", _format_currency(summary.get("net_flow", 0))),
        ("Total Transactions", str(summary.get("total_transactions", 0))),
        ("Unique Counterparties", str(summary.get("unique_counterparties", 0))),
        ("Financial Health Score", f"{summary.get('financial_health_score', 0)}/100"),
        ("Grade", summary.get("grade", "N/A")),
        ("Savings Rate", f"{summary.get('savings_rate', 0)}%"),
    ]

    for row_idx, row_data in enumerate(summary_data, start=3):
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws_summary.cell(row=row_idx, column=col_idx, value=value)
            if row_idx == 3:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment

    for col in ["A", "B"]:
        ws_summary.column_dimensions[col].width = 25

    # Sheet 2: Transactions
    ws_tx = wb.create_sheet("Transactions")

    headers = [
        "Date",
        "Description",
        "Counterparty",
        "Type",
        "Amount",
        "Category",
        "Reference",
        "Balance",
    ]

    for col_idx, header in enumerate(headers, start=1):
        cell = ws_tx.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    for row_idx, tx in enumerate(transactions, start=2):
        ws_tx.cell(row=row_idx, column=1, value=tx.get("date", ""))
        ws_tx.cell(row=row_idx, column=2, value=tx.get("description", "")[:100])
        ws_tx.cell(row=row_idx, column=3, value=tx.get("counterparty", ""))
        ws_tx.cell(
            row=row_idx,
            column=4,
            value="Sent" if tx.get("type") == "sent" else "Received",
        )
        ws_tx.cell(row=row_idx, column=5, value=tx.get("amount", 0))
        ws_tx.cell(row=row_idx, column=6, value=tx.get("category", "Uncategorized"))
        ws_tx.cell(row=row_idx, column=7, value=tx.get("reference", ""))
        ws_tx.cell(row=row_idx, column=8, value=tx.get("balance", ""))

        amount_cell = ws_tx.cell(row=row_idx, column=5)
        amount_cell.number_format = "#,##0.00"
        if tx.get("type") == "sent":
            amount_cell.font = Font(color="C0392B")
        else:
            amount_cell.font = Font(color="27AE60")

    for col_idx in range(1, len(headers) + 1):
        column_letter = get_column_letter(col_idx)
        ws_tx.column_dimensions[column_letter].width = 18

    # Sheet 3: Categories
    if "spending_breakdown" in summary and summary["spending_breakdown"]:
        ws_cat = wb.create_sheet("Categories")

        cat_headers = ["Category", "Amount", "Percentage"]
        for col_idx, header in enumerate(cat_headers, start=1):
            cell = ws_cat.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        for row_idx, cat in enumerate(summary["spending_breakdown"], start=2):
            ws_cat.cell(row=row_idx, column=1, value=cat.get("name", "Other"))
            ws_cat.cell(row=row_idx, column=2, value=cat.get("amount", 0))
            ws_cat.cell(row=row_idx, column=3, value=cat.get("percentage", 0))
            ws_cat.cell(row=row_idx, column=2).number_format = "#,##0.00"

        ws_cat.column_dimensions["A"].width = 25
        ws_cat.column_dimensions["B"].width = 15
        ws_cat.column_dimensions["C"].width = 12

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


# ============================================================
# SEARCH ENDPOINT WITH TIMING
# ============================================================


@router.get("/search")
async def search_entities(
    q: str = Query(..., min_length=2, description="Search query"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    🔍 SEARCH ENDPOINT
    Search for counterparties by name or phone number.
    """
    request_start = time.perf_counter()

    try:
        search_term = f"%{q}%"

        query_start = time.perf_counter()
        results = (
            db.query(
                Transaction.counterparty,
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "sent"
                    ),
                    0,
                ).label("sent"),
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "received"
                    ),
                    0,
                ).label("received"),
                func.count(Transaction.id).label("count"),
                func.min(Transaction.date).label("first_seen"),
                func.max(Transaction.date).label("last_seen"),
            )
            .filter(
                Transaction.tenant_id == tenant_id,
                or_(
                    Transaction.counterparty.ilike(search_term),
                    Transaction.description.ilike(search_term),
                ),
            )
            .group_by(Transaction.counterparty)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(10)
            .all()
        )
        query_time = (time.perf_counter() - query_start) * 1000
        logger.info(f"  ⏱️ SEARCH SQL: {query_time:.0f}ms")

        if not results:
            return {"results": []}

        serialize_start = time.perf_counter()
        response = {
            "results": [
                {
                    "name": r.counterparty,
                    "totalSent": float(r.sent or 0),
                    "totalReceived": float(r.received or 0),
                    "transactionCount": r.count,
                    "firstSeen": r.first_seen.isoformat() if r.first_seen else None,
                    "lastSeen": r.last_seen.isoformat() if r.last_seen else None,
                    "type": _detect_counterparty_type(r.counterparty or ""),
                }
                for r in results
            ]
        }
        serialize_time = (time.perf_counter() - serialize_start) * 1000
        logger.info(f"  ⏱️ SEARCH serialize: {serialize_time:.0f}ms")

        total_time = (time.perf_counter() - request_start) * 1000
        logger.info(f"📊 SEARCH TOTAL: {total_time:.0f}ms")

        return response

    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ============================================================
# CORE ANALYTICS ENDPOINTS WITH TIMING
# ============================================================


@router.get("/dashboard")
async def get_dashboard(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """🚀 OPTIMIZED DASHBOARD ENDPOINT WITH TIMING"""
    request_start = time.perf_counter()

    try:
        logger.info(f"📊 Dashboard request started for tenant: {tenant_id}")

        service_start = time.perf_counter()
        service = AnalyticsService(db, tenant_id)
        service_created = (time.perf_counter() - service_start) * 1000
        logger.info(f"  ⏱️ Service created: {service_created:.0f}ms")

        result_start = time.perf_counter()
        result = service.get_dashboard_data()
        result_time = (time.perf_counter() - result_start) * 1000
        logger.info(f"  ⏱️ get_dashboard_data: {result_time:.0f}ms")

        total_time = (time.perf_counter() - request_start) * 1000
        logger.info(f"📊 DASHBOARD TOTAL: {total_time:.0f}ms")

        return result

    except Exception as e:
        logger.error(f"Error in dashboard endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_analytics_summary(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get analytics summary for the current tenant WITH FULL TIMING"""
    total_start = time.perf_counter()
    print("=" * 60)
    print(f"📊 SUMMARY ENDPOINT ENTERED at {datetime.now().isoformat()}")
    print(f"📊 Tenant: {tenant_id}")

    # 1. Service creation
    service_start = time.perf_counter()
    service = AnalyticsService(db, tenant_id)
    service_elapsed = (time.perf_counter() - service_start) * 1000
    print(f"⏱️ SERVICE_CREATE={service_elapsed:.2f}ms")
    logger.info(f"⏱️ SERVICE_CREATE={service_elapsed:.2f}ms")

    # 2. _get_summary() method
    summary_start = time.perf_counter()
    result = service._get_summary()
    summary_elapsed = (time.perf_counter() - summary_start) * 1000
    print(f"⏱️ GET_SUMMARY_METHOD={summary_elapsed:.2f}ms")
    logger.info(f"⏱️ GET_SUMMARY_METHOD={summary_elapsed:.2f}ms")

    # 3. Total endpoint time
    total_elapsed = (time.perf_counter() - total_start) * 1000
    print(f"⏱️ SUMMARY_TOTAL={total_elapsed:.2f}ms")
    logger.info(f"⏱️ SUMMARY_TOTAL={total_elapsed:.2f}ms")
    print("=" * 60)

    return result


@router.get("/test-deps")
async def test_dependencies(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Test endpoint to check dependency timing"""
    import time

    start = time.perf_counter()

    # Just return the tenant and user info
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "tenant_id": tenant_id,
        "user_email": user.get("email"),
        "dependencies_ms": elapsed,
        "message": "Dependencies resolved!",
    }


@router.get("/insights")
async def get_insights(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get AI-style insights for the current tenant WITH TIMING"""
    request_start = time.perf_counter()

    try:
        logger.info(f"💡 Insights request started for tenant: {tenant_id}")

        service_start = time.perf_counter()
        service = AnalyticsService(db, tenant_id)
        service_created = (time.perf_counter() - service_start) * 1000
        logger.info(f"  ⏱️ Service created: {service_created:.0f}ms")

        summary_start = time.perf_counter()
        summary = service._get_summary()
        summary_time = (time.perf_counter() - summary_start) * 1000
        logger.info(f"  ⏱️ _get_summary: {summary_time:.0f}ms")

        insight_start = time.perf_counter()
        result = service._generate_basic_insights(summary)
        insight_time = (time.perf_counter() - insight_start) * 1000
        logger.info(f"  ⏱️ _generate_basic_insights: {insight_time:.0f}ms")

        total_time = (time.perf_counter() - request_start) * 1000
        logger.info(f"💡 INSIGHTS TOTAL: {total_time:.0f}ms")

        return result

    except Exception as e:
        logger.error(f"Error in insights endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🚀 OPTIMIZED PEOPLE-BUSINESSES WITH TIMING
# ============================================================


@router.get("/people-businesses")
async def get_people_businesses(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    🚀 OPTIMIZED: Get people and businesses using pure SQL aggregation.
    All aggregation done in PostgreSQL - NO Python loops.
    """
    request_start = time.perf_counter()

    try:
        logger.info(f"👥 People-Businesses request started for tenant: {tenant_id}")

        service_start = time.perf_counter()
        service = AnalyticsService(db, tenant_id)
        service_created = (time.perf_counter() - service_start) * 1000
        logger.info(f"  ⏱️ Service created: {service_created:.0f}ms")

        result_start = time.perf_counter()
        result = service.get_people_businesses()
        result_time = (time.perf_counter() - result_start) * 1000
        logger.info(f"  ⏱️ get_people_businesses: {result_time:.0f}ms")

        total_time = (time.perf_counter() - request_start) * 1000
        logger.info(f"👥 PEOPLE-BUSINESSES TOTAL: {total_time:.0f}ms")

        return result

    except Exception as e:
        logger.error(f"Error in people-businesses endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# FALLBACK: WORKING VERSION WITH PYTHON AGGREGATION
# ============================================================


@router.get("/people-businesses-legacy")
async def get_people_businesses_legacy(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    LEGACY FALLBACK: Get people and businesses using Python aggregation.
    Use this if the optimized version has issues.
    """
    try:
        start = time.perf_counter()

        transactions = (
            db.query(Transaction).filter(Transaction.tenant_id == tenant_id).all()
        )

        if not transactions:
            return {
                "counterparties": [],
                "total_counterparties": 0,
                "total_transactions": 0,
            }

        cp_sent = Counter()
        cp_received = Counter()
        cp_count = Counter()
        cp_first_seen = {}
        cp_last_seen = {}

        for t in transactions:
            if t.counterparty:
                amount = float(t.amount)
                cp_count[t.counterparty] += 1
                if (
                    t.counterparty not in cp_first_seen
                    or t.date < cp_first_seen[t.counterparty]
                ):
                    cp_first_seen[t.counterparty] = t.date
                if (
                    t.counterparty not in cp_last_seen
                    or t.date > cp_last_seen[t.counterparty]
                ):
                    cp_last_seen[t.counterparty] = t.date
                if t.transaction_type == "sent":
                    cp_sent[t.counterparty] += abs(amount)
                else:
                    cp_received[t.counterparty] += amount

        counterparties = [
            {
                "name": name,
                "totalSent": cp_sent.get(name, 0),
                "totalReceived": cp_received.get(name, 0),
                "count": cp_count.get(name, 0),
                "firstSeen": (
                    cp_first_seen.get(name).isoformat()
                    if cp_first_seen.get(name)
                    else None
                ),
                "lastSeen": (
                    cp_last_seen.get(name).isoformat()
                    if cp_last_seen.get(name)
                    else None
                ),
                "type": _detect_counterparty_type(name),
            }
            for name in cp_count.keys()
        ]

        counterparties.sort(
            key=lambda x: x["totalSent"] + x["totalReceived"], reverse=True
        )

        elapsed = time.perf_counter() - start
        logger.info(f"📊 People-businesses (legacy) took {elapsed:.3f}s")

        return {
            "counterparties": counterparties[:20],
            "total_counterparties": len(counterparties),
            "total_transactions": len(transactions),
        }

    except Exception as e:
        logger.error(f"Error in people-businesses legacy endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# OTHER ANALYTICS ENDPOINTS
# ============================================================


@router.get("/top-customers")
async def get_top_customers(
    limit: int = Query(5, ge=1, le=20),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get top customers by transaction volume."""
    try:
        service = AnalyticsService(db, tenant_id)
        return service._get_top_counterparties(limit=limit)
    except Exception as e:
        logger.error(f"Error in top customers endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spending-categories")
async def get_spending_categories(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get spending categories breakdown."""
    try:
        service = AnalyticsService(db, tenant_id)
        return service._get_spending_categories()
    except Exception as e:
        logger.error(f"Error in spending categories endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-score")
async def get_health_score(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get financial health score with breakdown."""
    try:
        service = AnalyticsService(db, tenant_id)
        summary = service._get_summary()
        return {
            "score": summary.get("financial_health_score", 0),
            "grade": summary.get("grade", "N/A"),
            "factors": [
                {"name": "Cash Flow", "value": summary.get("net_flow", 0)},
                {
                    "name": "Transaction Volume",
                    "value": summary.get("total_transactions", 0),
                },
                {"name": "Savings Rate", "value": summary.get("savings_rate", 0)},
            ],
        }
    except Exception as e:
        logger.error(f"Error in health score endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
async def get_analytics_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
    counterparty: Optional[str] = None,
):
    """Get transactions with pagination and optional counterparty filter."""
    try:
        query = db.query(Transaction).filter(Transaction.tenant_id == tenant_id)

        if counterparty:
            query = query.filter(Transaction.counterparty == counterparty)
            logger.info(f"🔍 Filtering transactions by counterparty: {counterparty}")

        transactions = (
            query.order_by(desc(Transaction.date)).offset(skip).limit(limit).all()
        )

        return [
            {
                "id": str(t.id),
                "transaction_id": t.transaction_id,
                "amount": float(t.amount),
                "transaction_type": t.transaction_type,
                "type": t.transaction_type,
                "counterparty": t.counterparty,
                "date": t.date.isoformat() if t.date else "",
                "description": t.description or "",
                "reference": t.reference or "",
                "category": t.category,
                "merchant": t.merchant,
                "balance": float(t.balance) if t.balance else None,
            }
            for t in transactions
        ]
    except Exception as e:
        logger.error(f"Error in transactions endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/count")
async def get_transactions_count(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get total transaction count for the tenant."""
    try:
        count = (
            db.query(func.count(Transaction.id))
            .filter(Transaction.tenant_id == tenant_id)
            .scalar()
            or 0
        )
        return {"count": count}
    except Exception as e:
        logger.error(f"Error in transactions count endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily")
async def get_daily_analytics(
    days: int = Query(7, ge=1, le=30),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get daily transaction totals for the last N days."""
    try:
        start_date = datetime.now() - timedelta(days=days)

        results = (
            db.query(
                func.date(Transaction.date).label("day"),
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .filter(Transaction.tenant_id == tenant_id, Transaction.date >= start_date)
            .group_by(func.date(Transaction.date))
            .order_by(func.date(Transaction.date))
            .all()
        )

        date_range = [(start_date + timedelta(days=i)).date() for i in range(days + 1)]
        result_dict = {
            str(r.day): float(abs(r.total)) if r.total else 0 for r in results
        }

        return [
            {"date": str(date), "amount": result_dict.get(str(date), 0.0)}
            for date in date_range
        ]
    except Exception as e:
        logger.error(f"Error in daily analytics endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transaction-types")
async def get_transaction_type_analysis(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get transaction breakdown by type."""
    try:
        results = (
            db.query(
                Transaction.transaction_type,
                func.sum(Transaction.amount).label("amount"),
                func.count(Transaction.id).label("count"),
            )
            .filter(Transaction.tenant_id == tenant_id)
            .group_by(Transaction.transaction_type)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        return [
            {
                "type": r.transaction_type or "unknown",
                "amount": float(abs(r.amount)) if r.amount else 0,
                "count": r.count,
            }
            for r in results
            if r.transaction_type
        ]
    except Exception as e:
        logger.error(f"Error in transaction types endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# EXPORT ENDPOINTS
# ============================================================


@router.get("/export/csv")
async def export_csv(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    format: str = Query("csv", regex="^(csv|excel)$", description="Export format"),
):
    """Export transactions in CSV or Excel format."""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)

        transactions = (
            db.query(Transaction)
            .filter(Transaction.tenant_id == tenant_id, Transaction.date >= cutoff_date)
            .order_by(Transaction.date.desc())
            .all()
        )

        if not transactions:
            raise HTTPException(status_code=404, detail="No transactions found")

        service = AnalyticsService(db, tenant_id)
        summary = service._get_summary()

        # ✅ Add spending_breakdown for Excel export
        spending_breakdown = service._get_spending_categories()
        summary["spending_breakdown"] = spending_breakdown

        tx_data = [
            {
                "date": t.date.isoformat() if t.date else "",
                "description": t.description or "",
                "counterparty": t.counterparty or "Unknown",
                "type": "sent" if t.transaction_type == "sent" else "received",
                "amount": float(t.amount),
                "category": t.category or "Uncategorized",
                "merchant": t.merchant or "",
                "reference": t.reference or "",
                "balance": float(t.balance) if t.balance else None,
            }
            for t in transactions
        ]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"financial_report_{tenant_id}_{timestamp}"

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            headers = [
                "Date",
                "Description",
                "Counterparty",
                "Type",
                "Amount",
                "Category",
                "Merchant",
                "Reference",
                "Balance",
            ]
            writer.writerow(headers)

            for tx in tx_data:
                writer.writerow(
                    [
                        tx["date"],
                        tx["description"],
                        tx["counterparty"],
                        "Sent" if tx["type"] == "sent" else "Received",
                        tx["amount"],
                        tx["category"],
                        tx["merchant"],
                        tx["reference"],
                        tx["balance"] if tx["balance"] is not None else "",
                    ]
                )

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
            )

        elif format == "excel":
            excel_data = _generate_excel_report(tx_data, summary)

            return StreamingResponse(
                iter([excel_data]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}.xlsx"
                },
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/dashboard/refresh")
async def refresh_dashboard_cache(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Force refresh of dashboard cache."""
    try:
        service = AnalyticsService(db, tenant_id)
        service.clear_cache()
        service.get_dashboard_data()
        return {
            "status": "refreshed",
            "message": "Dashboard cache cleared and refreshed",
        }
    except Exception as e:
        logger.error(f"Error refreshing dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ping")
async def ping():
    """Simple ping endpoint for testing"""
    import time

    start = time.perf_counter()
    time.sleep(0.01)  # Simulate work
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "status": "pong",
        "elapsed_ms": elapsed,
        "message": "Analytics router is alive!",
    }
