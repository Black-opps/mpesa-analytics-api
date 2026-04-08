"""
Analytics routes for MPesa Analytics API Gateway
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from src.core.database import get_db
from src.core.security import get_current_user
from src.models import Transaction, User

router = APIRouter()

# Add to your existing analytics.py

@router.get("/summary")
def analytics_summary(db: Session = Depends(get_db)):
    """Get analytics summary for dashboard."""
    total_transactions = db.query(func.count(Transaction.id)).scalar()
    total_amount = db.query(func.coalesce(func.sum(Transaction.amount), 0)).scalar()
    avg_transaction = db.query(func.coalesce(func.avg(Transaction.amount), 0)).scalar()
    
    # Calculate active days (example logic)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_days = db.query(func.count(func.distinct(func.date(Transaction.timestamp)))).filter(
        Transaction.timestamp >= thirty_days_ago
    ).scalar() or 0
    
    return {
        "total_transactions": total_transactions or 0,
        "total_amount": float(total_amount or 0),
        "average_transaction": float(avg_transaction or 0),
        "active_days": active_days
    }


@router.get("/customers")
def customer_summary(db: Session = Depends(get_db)):
    """Get customer analytics for dashboard."""
    unique_customers = db.query(
        func.count(func.distinct(Transaction.counterparty))
    ).scalar() or 0
    
    # Top customers by transaction volume
    top_customers = db.query(
        Transaction.counterparty,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
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
                "total": float(c.total),
                "count": c.count
            } for c in top_customers
        ]
    }


@router.get("/insights")
def insights_summary(db: Session = Depends(get_db)):
    """Get AI-style insights for dashboard."""
    largest = db.query(func.max(Transaction.amount)).scalar() or 0
    smallest = db.query(func.min(Transaction.amount)).scalar() or 0
    avg = db.query(func.avg(Transaction.amount)).scalar() or 0
    
    insights = []
    
    if largest > avg * 5:
        insights.append({
            "type": "alert",
            "message": f"Large transaction detected: KES {largest:.2f}",
            "suggestion": "Review this transaction for accuracy"
        })
    
    insights.append({
        "type": "insight",
        "message": f"Your average transaction is KES {avg:.2f}",
        "suggestion": "Track transactions above this amount"
    })
    
    return insights

@router.get("/analytics/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get analytics summary for the current user/tenant.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    
    total_amount = sum(t.amount for t in transactions)
    total_transactions = len(transactions)
    avg_transaction = total_amount / total_transactions if total_transactions > 0 else 0
    
    return {
        "total_transactions": total_transactions,
        "total_amount": total_amount,
        "average_transaction": avg_transaction
    }

@router.get("/analytics/transactions")
async def get_analytics_transactions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get transactions for analytics."""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.timestamp.desc()).offset(skip).limit(limit).all()
    
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

@router.get("/analytics/customers")
async def get_analytics_customers(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get customer analytics (unique counterparties)."""
    customers = db.query(
        Transaction.counterparty,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(Transaction.amount).label('total_volume'),
        func.max(Transaction.timestamp).label('last_transaction')
    ).filter(
        Transaction.user_id == current_user.id
    ).group_by(
        Transaction.counterparty
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(limit).all()
    
    return [
        {
            "customer_id": c.counterparty,
            "phone": c.counterparty,
            "transaction_count": c.transaction_count,
            "total_volume": float(c.total_volume) if c.total_volume else 0,
            "last_transaction": c.last_transaction.isoformat() if c.last_transaction else None
        } for c in customers
    ]

@router.get("/analytics/insights")
async def get_analytics_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get insights based on transaction patterns."""
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
    
    total = sum(t.amount for t in transactions)
    avg = total / len(transactions)
    
    insights.append({
        "type": "spending",
        "message": f"Your average transaction is KES {avg:.2f}",
        "suggestion": "Track large transactions for better budgeting."
    })
    
    large_tx = [t for t in transactions if t.amount > avg * 2]
    if large_tx:
        insights.append({
            "type": "alert",
            "message": f"You have {len(large_tx)} large transactions above your average",
            "suggestion": "Review these transactions for accuracy."
        })
    
    return insights
