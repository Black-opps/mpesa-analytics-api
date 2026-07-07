"""
MPesa Analytics API - Complete Version
Integrates with Auth Service for authentication
"""

import asyncio
import os
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

# Import local modules
from src.core.database import Transaction, get_db, init_db
from src.core.dependencies import get_current_tenant_id, get_current_user
from src.messaging import EventBus
from src.routers import analytics as analytics_router
from src.services.auth_client import auth_client

load_dotenv()

# ============================================================
# LIFESPAN MANAGER - Handles startup and shutdown
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    print("[START] Starting Analytics Service...")

    # Initialize database
    init_db()
    print("[OK] Database initialized")

    # Connect to RabbitMQ
    bus = EventBus()
    connected = await bus.connect()
    if connected:
        asyncio.create_task(
            bus.consume(
                "transactions.analyzed.q", "transactions.analyzed", ingest_from_queue
            )
        )
        print("[OK] Analytics listening on transactions.analyzed queue")
    else:
        print("[WARN] RabbitMQ not available - HTTP-only mode")

    # Yield control - app is running
    yield

    # Shutdown
    print("[SHUTDOWN] Shutting down Analytics Service...")
    await bus.close()
    await auth_client.close()
    print("[OK] Shutdown complete")


# ============================================================
# CREATE FASTAPI APP
# ============================================================

app = FastAPI(title="Analytics Service", version="2.0.0", lifespan=lifespan)

# ============================================================
# INCLUDE ROUTERS
# ============================================================

app.include_router(analytics_router.router)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RABBITMQ CONSUMER
# ============================================================


async def ingest_from_queue(event: dict):
    """Consumer for transactions.analyzed queue"""
    trace_id = event.get("trace_id", "unknown")
    tenant_id = event.get("tenant_id", "test_tenant")

    data = event.get("data", {})
    transactions = data.get("transactions", [])
    file_name = data.get("file_name", "unknown")

    print(
        f"[{trace_id}] 📥 Ingesting {len(transactions)} transactions for tenant {tenant_id}"
    )

    db = next(get_db())

    try:
        new_count = 0
        for txn in transactions:
            existing = (
                db.query(Transaction)
                .filter(
                    Transaction.transaction_id == txn.get("transaction_id"),
                    Transaction.tenant_id == tenant_id,
                )
                .first()
            )

            if not existing:
                txn_date = txn.get("date")
                if isinstance(txn_date, str):
                    try:
                        txn_date = datetime.fromisoformat(
                            txn_date.replace("Z", "+00:00")
                        )
                    except:
                        txn_date = datetime.now()
                else:
                    txn_date = datetime.now()

                new_transaction = Transaction(
                    tenant_id=tenant_id,
                    transaction_id=txn.get("transaction_id"),
                    date=txn_date,
                    amount=float(txn.get("amount", 0)),
                    transaction_type=txn.get("transaction_type"),
                    counterparty=txn.get("counterparty", ""),
                    category=txn.get("category", "Uncategorized"),
                    description=txn.get("description", "")[:500],
                    created_at=datetime.utcnow(),
                )
                db.add(new_transaction)
                new_count += 1

        db.commit()
        print(f"[{trace_id}] [OK] Ingested {new_count} new transactions")

    except Exception as e:
        db.rollback()
        print(f"[{trace_id}] [ERROR] Failed to ingest: {e}")
        raise
    finally:
        db.close()


# ============================================================
# HEALTH ENDPOINTS
# ============================================================


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "analytics"}


@app.get("/")
async def root():
    return {"service": "Analytics Service", "version": "2.0.0", "status": "running"}


# ============================================================
# ANALYTICS ENDPOINTS (Legacy - kept for compatibility)
# ============================================================


@app.get("/api/v1/analytics/dashboard")
async def get_dashboard(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    🚀 OPTIMIZED DASHBOARD ENDPOINT
    Returns ALL dashboard data in a SINGLE optimized query.
    Uses JWT authentication via Auth Service.
    """
    try:
        # Get all transactions for this tenant
        transactions = (
            db.query(Transaction).filter(Transaction.tenant_id == tenant_id).all()
        )

        print(f"📊 Found {len(transactions)} transactions for tenant: {tenant_id}")

        if not transactions:
            return {
                "summary": {
                    "money_in": 0,
                    "money_out": 0,
                    "net_flow": 0,
                    "total_transactions": 0,
                    "unique_counterparties": 0,
                    "income_consistency": "N/A",
                    "spending_discipline": "N/A",
                    "transaction_stability": "N/A",
                    "savings_rate": 0,
                },
                "recent_transactions": [],
                "top_counterparties": [],
                "spending_breakdown": [],
                "insights": [],
                "health_score": {"score": 0, "grade": "N/A", "savings_rate": 0},
                "financial_health": {"score": 0, "grade": "N/A", "factors": []},
                "activity_summary": {
                    "recent_transactions": 0,
                    "total_transactions": 0,
                    "days_active": 0,
                    "average_daily": 0,
                    "monthly_average": 0,
                },
            }

        # ✅ Convert Decimal to float for all amounts
        total_sent = sum(
            float(abs(t.amount)) for t in transactions if t.transaction_type == "sent"
        )
        total_received = sum(
            float(t.amount) for t in transactions if t.transaction_type == "received"
        )
        net_flow = total_received - total_sent
        total_transactions = len(transactions)

        # Get unique counterparties
        counterparties = list(
            set(t.counterparty for t in transactions if t.counterparty)
        )
        unique_counterparties = len(counterparties)

        # Get date range
        dates = [t.date for t in transactions if t.date]
        if dates:
            start_date = min(dates)
            end_date = max(dates)
            days_active = (end_date - start_date).days + 1
            monthly_average = round(total_transactions / max(1, days_active / 30), 1)
            average_daily = round(total_transactions / max(1, days_active), 1)
        else:
            days_active = 0
            monthly_average = 0
            average_daily = 0

        # Calculate health score
        health_score = 70
        if net_flow > 0:
            health_score += min(20, (net_flow / 10000) * 5)
        if total_transactions > 100:
            health_score += 10
        if total_transactions > 500:
            health_score += 5
        if net_flow < 0:
            health_score -= min(20, (abs(net_flow) / 10000) * 5)
        health_score = max(0, min(100, health_score))

        grade = "Poor"
        if health_score >= 80:
            grade = "Excellent"
        elif health_score >= 65:
            grade = "Good"
        elif health_score >= 50:
            grade = "Fair"

        savings_rate = round(
            (
                ((total_received - total_sent) / total_received * 100)
                if total_received > 0
                else 0
            ),
            1,
        )

        # Get recent transactions (last 10)
        recent = (
            db.query(Transaction)
            .filter(Transaction.tenant_id == tenant_id)
            .order_by(Transaction.date.desc())
            .limit(10)
            .all()
        )

        recent_transactions = [
            {
                "id": str(t.id),
                "date": t.date.isoformat() if t.date else "",
                "amount": float(t.amount),
                "type": "sent" if t.transaction_type == "sent" else "received",
                "counterparty": t.counterparty or "Unknown",
                "description": t.description or "",
                "reference": t.transaction_id or "",
                "time_ago": _get_time_ago(t.date) if t.date else "",
            }
            for t in recent
        ]

        # Get top counterparties
        cp_counter = {}
        cp_sent = {}
        cp_received = {}
        cp_count = {}

        for t in transactions:
            if t.counterparty:
                amount = float(t.amount)
                cp_counter[t.counterparty] = cp_counter.get(t.counterparty, 0) + abs(
                    amount
                )
                cp_count[t.counterparty] = cp_count.get(t.counterparty, 0) + 1
                if t.transaction_type == "sent":
                    cp_sent[t.counterparty] = cp_sent.get(t.counterparty, 0) + abs(
                        amount
                    )
                else:
                    cp_received[t.counterparty] = (
                        cp_received.get(t.counterparty, 0) + amount
                    )

        # Sort and get top 5
        top_counterparties = sorted(
            [
                {
                    "name": k,
                    "totalSent": cp_sent.get(k, 0),
                    "totalReceived": cp_received.get(k, 0),
                    "count": cp_count.get(k, 0),
                    "type": _detect_counterparty_type(k),
                }
                for k in cp_counter.keys()
            ],
            key=lambda x: x["totalSent"] + x["totalReceived"],
            reverse=True,
        )[:5]

        # Get spending categories
        category_totals = {}
        for t in transactions:
            if t.transaction_type == "sent":
                cat = t.category or "Uncategorized"
                category_totals[cat] = category_totals.get(cat, 0) + float(
                    abs(t.amount)
                )

        total_spent = sum(category_totals.values())
        spending_breakdown = [
            {
                "name": cat,
                "amount": round(amount, 2),
                "percentage": round(
                    (amount / total_spent * 100) if total_spent > 0 else 0, 1
                ),
            }
            for cat, amount in sorted(
                category_totals.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]

        # Generate insights
        insights = _generate_insights(
            total_transactions, net_flow, total_received, total_sent, category_totals
        )

        # Financial health factors
        factors = []
        if net_flow > 0:
            factors.append(
                {
                    "name": "Cash Flow",
                    "score": min(100, 50 + (net_flow / 10000) * 10),
                    "description": "Positive cash flow indicates healthy financial management.",
                }
            )
        else:
            factors.append(
                {
                    "name": "Cash Flow",
                    "score": max(0, 50 - (abs(net_flow) / 10000) * 10),
                    "description": "Negative cash flow may indicate overspending.",
                }
            )

        if unique_counterparties >= 2:
            factors.append(
                {
                    "name": "Income Stability",
                    "score": 80,
                    "description": "Multiple income sources reduce financial risk.",
                }
            )
        else:
            factors.append(
                {
                    "name": "Income Stability",
                    "score": 50,
                    "description": "Consider diversifying your income sources.",
                }
            )

        return {
            "summary": {
                "money_in": round(total_received, 2),
                "money_out": round(total_sent, 2),
                "net_flow": round(net_flow, 2),
                "total_transactions": total_transactions,
                "unique_counterparties": unique_counterparties,
                "income_consistency": (
                    "Strong" if total_received > total_sent * 1.2 else "Moderate"
                ),
                "spending_discipline": (
                    "Strong" if total_sent < total_received * 0.7 else "Moderate"
                ),
                "transaction_stability": (
                    "Strong" if total_transactions > 20 else "Building"
                ),
                "savings_rate": savings_rate,
            },
            "recent_transactions": recent_transactions,
            "top_counterparties": top_counterparties,
            "spending_breakdown": spending_breakdown,
            "insights": insights,
            "health_score": {
                "score": round(health_score),
                "grade": grade,
                "savings_rate": savings_rate,
            },
            "financial_health": {
                "score": round(health_score),
                "grade": grade,
                "factors": factors[:5],
            },
            "activity_summary": {
                "recent_transactions": len(recent),
                "total_transactions": total_transactions,
                "days_active": days_active,
                "average_daily": average_daily,
                "monthly_average": monthly_average,
            },
        }

    except Exception as e:
        import traceback

        print(f"Error in dashboard endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to load dashboard data: {str(e)}"
        )


@app.get("/api/v1/analytics/summary")
async def get_analytics_summary(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get analytics summary for the current tenant."""
    try:
        transactions = (
            db.query(Transaction).filter(Transaction.tenant_id == tenant_id).all()
        )

        if not transactions:
            return {
                "total_transactions": 0,
                "total_sent": 0.0,
                "total_received": 0.0,
                "total_amount": 0.0,
                "average_transaction": 0.0,
                "tenant_id": tenant_id,
            }

        total_sent = sum(
            abs(float(t.amount)) for t in transactions if t.transaction_type == "sent"
        )
        total_received = sum(
            float(t.amount) for t in transactions if t.transaction_type == "received"
        )

        return {
            "total_transactions": len(transactions),
            "total_sent": round(total_sent, 2),
            "total_received": round(total_received, 2),
            "total_amount": round(total_received - total_sent, 2),
            "average_transaction": (
                round((total_received - total_sent) / len(transactions), 2)
                if transactions
                else 0
            ),
            "tenant_id": tenant_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# DEBUG ENDPOINTS
# ============================================================


@app.get("/api/v1/analytics/debug/db-check")
async def debug_db_check(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Debug endpoint to check database for tenant data"""

    print(f"🔍 Debug DB Check - Tenant: {tenant_id}")

    # 1. Count all transactions in the database (no filter)
    total_all = db.query(func.count(Transaction.id)).scalar()
    print(f"📊 Total transactions in DB: {total_all}")

    # 2. Count transactions for this tenant
    tenant_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.tenant_id == tenant_id)
        .scalar()
    )
    print(f"📊 Transactions for tenant {tenant_id}: {tenant_count}")

    # 3. Get all distinct tenant_ids
    distinct_tenants = db.query(Transaction.tenant_id).distinct().all()
    tenant_ids = [t[0] for t in distinct_tenants]
    print(f"📊 Distinct tenant IDs: {tenant_ids}")

    # 4. Get sample transaction
    sample = db.query(Transaction).filter(Transaction.tenant_id == tenant_id).first()

    # 5. Get sum of amounts
    total_amount = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.tenant_id == tenant_id)
        .scalar()
    )

    return {
        "tenant_id": tenant_id,
        "total_transactions_in_db": total_all,
        "tenant_transaction_count": tenant_count,
        "distinct_tenant_ids": tenant_ids,
        "has_transactions": tenant_count > 0,
        "total_amount": float(total_amount) if total_amount else 0,
        "sample_transaction": (
            {
                "id": str(sample.id) if sample else None,
                "date": sample.date.isoformat() if sample else None,
                "amount": float(sample.amount) if sample else None,
                "counterparty": sample.counterparty if sample else None,
                "transaction_type": sample.transaction_type if sample else None,
            }
            if sample
            else None
        ),
    }


@app.get("/api/v1/analytics/transactions")
async def get_transactions(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    counterparty: Optional[str] = None,
):
    """Get transactions for analytics with pagination and optional counterparty filter."""
    try:
        # Start with base query
        query = db.query(Transaction).filter(Transaction.tenant_id == tenant_id)

        # Apply counterparty filter if provided
        if counterparty:
            query = query.filter(Transaction.counterparty == counterparty)
            print(f"🔍 Filtering transactions by counterparty: {counterparty}")

        # Get total count
        total = query.count()

        # Get transactions
        transactions = (
            query.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()
        )

        return {
            "transactions": [
                {
                    "id": str(t.id),
                    "transaction_id": t.transaction_id,
                    "date": t.date.isoformat() if t.date else None,
                    "amount": float(t.amount),
                    "type": t.transaction_type,
                    "transaction_type": t.transaction_type,
                    "counterparty": t.counterparty,
                    "category": t.category,
                    "description": t.description,
                    "reference": t.transaction_id,
                    "balance": float(t.balance) if t.balance else None,
                }
                for t in transactions
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
            "counterparty": counterparty,
            "tenant_id": tenant_id,
        }
    except Exception as e:
        print(f"❌ Error in transactions endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/transaction-types")
async def get_transaction_types(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get transaction breakdown by type."""
    try:
        results = (
            db.query(
                Transaction.transaction_type,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .filter(Transaction.tenant_id == tenant_id)
            .group_by(Transaction.transaction_type)
            .all()
        )

        return [
            {
                "type": r.transaction_type or "unknown",
                "total": float(abs(r.total)) if r.total else 0,
                "count": r.count,
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/categories")
async def get_category_breakdown(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get spending categories breakdown."""
    try:
        expense_results = (
            db.query(
                Transaction.category,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .filter(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_type == "sent",
            )
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        income_results = (
            db.query(
                Transaction.category,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .filter(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_type == "received",
            )
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        return {
            "expenses": [
                {
                    "category": r.category or "Uncategorized",
                    "total": float(abs(r.total)) if r.total else 0,
                    "count": r.count,
                }
                for r in expense_results
            ],
            "income": [
                {
                    "category": r.category or "Uncategorized",
                    "total": float(r.total) if r.total else 0,
                    "count": r.count,
                }
                for r in income_results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/top-customers")
async def get_top_customers(
    limit: int = 5,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get top customers by transaction volume."""
    try:
        cp_counter = {}
        cp_count = {}

        transactions = (
            db.query(Transaction).filter(Transaction.tenant_id == tenant_id).all()
        )

        for t in transactions:
            if t.counterparty:
                amount = float(abs(t.amount))
                cp_counter[t.counterparty] = cp_counter.get(t.counterparty, 0) + amount
                cp_count[t.counterparty] = cp_count.get(t.counterparty, 0) + 1

        # Sort and get top limit
        sorted_customers = sorted(
            [
                {"phone": k, "total": v, "count": cp_count.get(k, 0)}
                for k, v in cp_counter.items()
            ],
            key=lambda x: x["total"],
            reverse=True,
        )[:limit]

        return sorted_customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/insights")
async def get_insights(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get AI-style insights for the current tenant."""
    try:
        transactions = (
            db.query(Transaction).filter(Transaction.tenant_id == tenant_id).all()
        )

        if not transactions:
            return [
                {
                    "type": "insight",
                    "title": "Upload your first statement",
                    "description": "Upload an M-PESA statement to see personalized financial insights.",
                    "confidence": 0,
                }
            ]

        total_sent = sum(
            abs(float(t.amount)) for t in transactions if t.transaction_type == "sent"
        )
        total_received = sum(
            float(t.amount) for t in transactions if t.transaction_type == "received"
        )
        net_flow = total_received - total_sent
        total_transactions = len(transactions)

        # Get category totals
        category_totals = {}
        for t in transactions:
            if t.transaction_type == "sent":
                cat = t.category or "Uncategorized"
                category_totals[cat] = category_totals.get(cat, 0) + abs(
                    float(t.amount)
                )

        return _generate_insights(
            total_transactions, net_flow, total_received, total_sent, category_totals
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/daily-stats")
async def get_daily_stats(
    days: int = 30,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get daily transaction stats for the last N days."""
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
            .order_by(func.date(Transaction.date).desc())
            .all()
        )

        return [
            {
                "date": str(r.day),
                "total": float(r.total) if r.total else 0,
                "count": r.count,
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/health-score")
async def get_health_score(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get financial health score with breakdown."""
    try:
        transactions = (
            db.query(Transaction).filter(Transaction.tenant_id == tenant_id).all()
        )

        if not transactions:
            return {
                "score": 0,
                "grade": "N/A",
                "savings_rate": 0,
            }

        total_sent = sum(
            abs(float(t.amount)) for t in transactions if t.transaction_type == "sent"
        )
        total_received = sum(
            float(t.amount) for t in transactions if t.transaction_type == "received"
        )
        net_flow = total_received - total_sent
        total_transactions = len(transactions)

        health_score = 70
        if net_flow > 0:
            health_score += min(20, (net_flow / 10000) * 5)
        if total_transactions > 100:
            health_score += 10
        if net_flow < 0:
            health_score -= min(20, (abs(net_flow) / 10000) * 5)
        health_score = max(0, min(100, health_score))

        grade = "Poor"
        if health_score >= 80:
            grade = "Excellent"
        elif health_score >= 65:
            grade = "Good"
        elif health_score >= 50:
            grade = "Fair"

        savings_rate = round(
            (
                ((total_received - total_sent) / total_received * 100)
                if total_received > 0
                else 0
            ),
            1,
        )

        return {
            "score": round(health_score),
            "grade": grade,
            "savings_rate": savings_rate,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analytics/dashboard/refresh")
async def refresh_dashboard_cache(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Force refresh of dashboard cache."""
    try:
        return await get_dashboard(tenant_id, db, user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analytics/ingest")
async def ingest_single_transaction(
    request: Request,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """HTTP endpoint for Cashflow service to send processed transactions"""
    data = await request.json()
    tenant_id = data.get("tenant_id") or request.headers.get("X-Tenant-ID")

    if not tenant_id:
        tenant_id = user.get("tenant_id", "test_tenant")

    transactions = data.get("transactions", [])
    summary = data.get("summary", {})

    print(f"Ingesting {len(transactions)} transactions for tenant {tenant_id}")

    new_count = 0
    duplicate_count = 0

    for txn in transactions:
        existing = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_id == txn.get("transaction_id"),
                Transaction.tenant_id == tenant_id,
            )
            .first()
        )

        if not existing:
            txn_date = txn.get("date")
            if isinstance(txn_date, str):
                try:
                    txn_date = datetime.fromisoformat(txn_date.replace("Z", "+00:00"))
                except:
                    txn_date = datetime.now()
            else:
                txn_date = datetime.now()

            new_transaction = Transaction(
                tenant_id=tenant_id,
                transaction_id=txn.get("transaction_id"),
                date=txn_date,
                amount=float(txn.get("amount", 0)),
                transaction_type=txn.get("transaction_type"),
                counterparty=txn.get("counterparty", ""),
                category=txn.get("category", "Uncategorized"),
                description=txn.get("description", ""),
                created_at=datetime.utcnow(),
            )
            db.add(new_transaction)
            new_count += 1
        else:
            duplicate_count += 1

    db.commit()

    return {
        "status": "success",
        "ingested": new_count,
        "duplicates": duplicate_count,
        "message": f"Ingested {new_count} new transactions",
    }


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def _get_time_ago(date: datetime) -> str:
    """Calculate time ago string"""
    if not date:
        return "Unknown"
    diff = datetime.now() - date
    if diff.days > 0:
        return f"{diff.days} days ago"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    if diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    return "Just now"


def _detect_counterparty_type(name: str) -> str:
    """Detect counterparty type"""
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
    ]
    utility_keywords = [
        "Safaricom",
        "KPLC",
        "Water",
        "Internet",
        "Bill",
        "Token",
        "Electricity",
    ]

    if any(k in name for k in utility_keywords):
        return "utility"
    if any(k in name for k in business_keywords):
        return "business"
    if name.startswith("07") and len(name) >= 10:
        return "person"
    if name.startswith("01") and len(name) >= 10:
        return "person"
    if name.startswith("+254") and len(name) >= 12:
        return "person"
    return "unknown"


def _generate_insights(
    total_transactions, net_flow, total_received, total_sent, category_totals
):
    """Generate insights from transaction data"""
    insights = []

    # Cash flow insight
    if abs(net_flow) < 50000:
        insights.append(
            {
                "type": "insight",
                "title": "Near Breakeven Operation",
                "description": f"Your finances operated within {abs(net_flow / max(total_received, 1) * 100):.1f}% of breakeven.",
                "confidence": 96,
                "impact": "Small efficiency improvements could move you into positive territory.",
                "actionLabel": "Analyze Efficiency",
            }
        )
    elif net_flow < 0:
        insights.append(
            {
                "type": "warning",
                "title": "Cash Flow Deficit",
                "description": f"Outflows exceed inflows by KES {abs(net_flow):,.0f}.",
                "confidence": 94,
                "impact": "Review your top spending categories for potential savings.",
                "actionLabel": "Review Spending",
            }
        )
    else:
        insights.append(
            {
                "type": "positive",
                "title": "Positive Cash Flow",
                "description": f"You have a surplus of KES {net_flow:,.0f}.",
                "confidence": 94,
                "impact": "This provides room for savings or investment.",
                "actionLabel": "Create Savings Plan",
            }
        )

    # Transaction volume insight
    if total_transactions > 100:
        insights.append(
            {
                "type": "positive",
                "title": f"High transaction volume: {total_transactions:,} transactions",
                "description": f"You average {total_transactions // 12:,} transactions per month.",
                "confidence": 92,
                "impact": "Your activity level is in the top tier of users.",
                "actionLabel": "View Activity",
            }
        )

    # Top category insight
    if category_totals:
        top_cat = max(category_totals.items(), key=lambda x: x[1])
        if top_cat[0] != "Uncategorized":
            total_spent = sum(category_totals.values())
            pct = round(top_cat[1] / total_spent * 100) if total_spent > 0 else 0
            insights.append(
                {
                    "type": "insight" if pct < 40 else "warning",
                    "title": f"{top_cat[0]} is {pct}% of spending",
                    "description": f"Your top spending category is {top_cat[0]} at KES {top_cat[1]:,.0f}.",
                    "confidence": 88,
                    "impact": f"Reducing this category by 20% could save KES {round(top_cat[1] * 0.2):,}.",
                    "actionLabel": "Analyze Category",
                }
            )

    return insights[:5]


# ============================================================
# RUN THE APP
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)
