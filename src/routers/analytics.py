"""
Analytics routes for MPesa Analytics Service
All endpoints use JWT for tenant/user identification - no tenant_id in URL
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from src.core.database import get_db
from src.core.security import get_current_user
from src.models import Transaction, User

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# ==================== Main Analytics Endpoints ====================

@router.get("/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get analytics summary for the current user/tenant.
    Tenant ID is extracted from JWT token, not from URL.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    
    total_sent = sum(t.amount for t in transactions if t.amount < 0)
    total_received = sum(t.amount for t in transactions if t.amount > 0)
    total_transactions = len(transactions)
    
    return {
        "total_transactions": total_transactions,
        "total_sent": float(abs(total_sent)),
        "total_received": float(total_received),
        "total_amount": float(total_received - abs(total_sent)),
        "average_transaction": float((total_received - abs(total_sent)) / total_transactions) if total_transactions > 0 else 0,
        "active_days": 0
    }


@router.get("/customers")
async def get_customers_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get customer analytics for the current user/tenant.
    """
    unique_customers = db.query(
        func.count(func.distinct(Transaction.counterparty))
    ).filter(
        Transaction.user_id == current_user.id
    ).scalar() or 0
    
    # Top customers by transaction volume
    top_customers = db.query(
        Transaction.counterparty,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == current_user.id
    ).group_by(
        Transaction.counterparty
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(5).all()
    
    return {
        "total_customers": unique_customers,
        "top_customers": [
            {
                "phone": c.counterparty,
                "total": float(abs(c.total)) if c.total else 0,
                "count": c.count
            } for c in top_customers if c.counterparty
        ]
    }


@router.get("/insights")
async def get_insights_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-style insights for the current user/tenant.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    
    insights = []
    
    if not transactions:
        insights.append({
            "type": "info",
            "message": "Start adding transactions to see insights!",
            "suggestion": "Upload your M-Pesa statement to get started."
        })
        return insights
    
    total = sum(abs(t.amount) for t in transactions)
    avg = total / len(transactions)
    
    insights.append({
        "type": "spending",
        "message": f"Your average transaction is KES {avg:.2f}",
        "suggestion": "Track large transactions for better budgeting."
    })
    
    large_tx = [t for t in transactions if abs(t.amount) > avg * 2]
    if large_tx:
        insights.append({
            "type": "alert",
            "message": f"You have {len(large_tx)} large transactions above your average",
            "suggestion": "Review these transactions for accuracy."
        })
    
    # Find most common transaction type
    from collections import Counter
    type_counts = Counter(t.transaction_type for t in transactions if t.transaction_type)
    if type_counts:
        most_common = type_counts.most_common(1)[0]
        insights.append({
            "type": "insight",
            "message": f"Your most frequent transaction type is '{most_common[0]}' ({most_common[1]} times)",
            "suggestion": "Consider setting up auto-categorization for this type."
        })
    
    return insights


# ==================== Extended Analytics Endpoints ====================

@router.get("/daily")
async def get_daily_analytics(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily transaction totals for the last N days.
    """
    start_date = datetime.now() - timedelta(days=days)
    
    results = db.query(
        func.date(Transaction.timestamp).label('date'),
        func.sum(Transaction.amount).label('amount')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.timestamp >= start_date
    ).group_by(
        func.date(Transaction.timestamp)
    ).order_by(
        func.date(Transaction.timestamp)
    ).all()
    
    # Fill in missing dates with zero amounts
    date_range = [(start_date + timedelta(days=i)).date() for i in range(days + 1)]
    result_dict = {str(r.date): float(abs(r.amount)) if r.amount else 0 for r in results}
    
    return [
        {
            "date": str(date),
            "amount": result_dict.get(str(date), 0.0)
        }
        for date in date_range
    ]


@router.get("/transaction-types")
async def get_transaction_type_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get transaction breakdown by type.
    """
    results = db.query(
        Transaction.transaction_type,
        func.sum(Transaction.amount).label('amount'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == current_user.id
    ).group_by(
        Transaction.transaction_type
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).all()
    
    return [{
        "type": r.transaction_type or 'unknown',
        "amount": float(abs(r.amount)) if r.amount else 0,
        "count": r.count
    } for r in results if r.transaction_type]


@router.get("/top-customers")
async def get_top_customers(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top customers by transaction volume.
    """
    results = db.query(
        Transaction.counterparty,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.counterparty.isnot(None)
    ).group_by(
        Transaction.counterparty
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(limit).all()
    
    return [{
        "counterparty": r.counterparty,
        "total": float(abs(r.total)) if r.total else 0,
        "count": r.count
    } for r in results if r.counterparty]


# ==================== Transaction Endpoints ====================

@router.get("/transactions")
async def get_analytics_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get transactions for analytics with pagination.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(
        Transaction.timestamp.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "id": t.id,
            "transaction_id": t.transaction_id,
            "amount": t.amount,
            "transaction_type": t.transaction_type,
            "counterparty": t.counterparty,
            "timestamp": t.timestamp.isoformat(),
            "user_id": t.user_id
        } for t in transactions
    ]