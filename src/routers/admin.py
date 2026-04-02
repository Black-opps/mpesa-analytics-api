# app/routers/admin.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List
from datetime import datetime, timedelta
import logging

from src.core.database import get_db
from src.dependencies.security import require_admin_user
from src.models import User, Transaction

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


# ==================== SYSTEM ANALYTICS ====================

@router.get("/analytics/system")
def get_system_analytics(
    db: Session = Depends(get_db),
    admin=Depends(require_admin_user),
):
    """
    Admin: Get system-wide analytics across ALL users
    """

    users_data = db.query(
        User.id,
        User.email,
        func.count(Transaction.id).label("transaction_count"),
        func.sum(Transaction.amount).label("total_volume"),
        func.count(func.distinct(Transaction.counterparty)).label(
            "unique_customers"
        ),
    ).outerjoin(
        Transaction,
        User.id == Transaction.user_id,
    ).group_by(
        User.id
    ).all()

    total_users = db.query(User).count()

    total_transactions = db.query(Transaction).count()

    total_volume = (
        db.query(func.sum(Transaction.amount)).scalar() or 0
    )

    total_customers = db.query(
        func.count(func.distinct(Transaction.counterparty))
    ).scalar() or 0

    sent_types = [
        "send_money",
        "pay_bill",
        "buy_goods",
        "withdraw",
    ]

    received_types = [
        "receive_money"
    ]

    total_sent = db.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.transaction_type.in_(sent_types)
    ).scalar() or 0

    total_received = db.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.transaction_type.in_(received_types)
    ).scalar() or 0

    return {
        "system_totals": {
            "total_users": total_users,
            "total_transactions": total_transactions,
            "total_volume": float(total_volume),
            "total_sent": float(total_sent),
            "total_received": float(total_received),
            "total_customers": total_customers,
        },
        "users_breakdown": [
            {
                "user_id": u.id,
                "email": u.email,
                "transactions": u.transaction_count or 0,
                "volume": float(u.total_volume)
                if u.total_volume
                else 0,
                "customers": u.unique_customers or 0,
            }
            for u in users_data
        ],
    }


# ==================== USER LIST ====================

@router.get("/users", response_model=List[dict])
def get_all_users(
    db: Session = Depends(get_db),
    admin=Depends(require_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):

    users = db.query(
        User.id,
        User.email,
        User.role,
        User.is_active,
        User.created_at,
        func.count(Transaction.id).label(
            "transaction_count"
        ),
        func.sum(Transaction.amount).label(
            "total_volume"
        ),
    ).outerjoin(
        Transaction,
        User.id == Transaction.user_id,
    ).group_by(
        User.id
    ).offset(skip).limit(limit).all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": (
                u.created_at.isoformat()
                if u.created_at
                else None
            ),
            "transaction_count": (
                u.transaction_count or 0
            ),
            "total_volume": (
                float(u.total_volume)
                if u.total_volume
                else 0
            ),
        }
        for u in users
    ]


# ==================== SINGLE USER ====================

@router.get("/users/{user_id}")
def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_user),
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).all()

    sent_types = [
        "send_money",
        "pay_bill",
        "buy_goods",
        "withdraw",
    ]

    total_sent = sum(
        t.amount
        for t in transactions
        if t.transaction_type in sent_types
    )

    unique_customers = len(
        set(t.counterparty for t in transactions)
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": (
                user.created_at.isoformat()
                if user.created_at
                else None
            ),
        },
        "stats": {
            "total_transactions": len(
                transactions
            ),
            "total_sent": total_sent,
            "unique_customers": unique_customers,
        },
    }


# ==================== DAILY ANALYTICS ====================

@router.get("/analytics/daily")
def get_admin_daily_analytics(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_user),
):

    start_date = datetime.utcnow() - timedelta(days=days)

    results = db.query(
        func.date(Transaction.timestamp).label(
            "date"
        ),
        func.count(Transaction.id).label(
            "transactions"
        ),
        func.sum(Transaction.amount).label(
            "volume"
        ),
        func.count(
            func.distinct(Transaction.user_id)
        ).label("active_users"),
    ).filter(
        Transaction.timestamp >= start_date
    ).group_by(
        func.date(Transaction.timestamp)
    ).order_by(
        func.date(Transaction.timestamp)
    ).all()

    return [
        {
            "date": str(r.date),
            "transactions": r.transactions,
            "volume": float(r.volume)
            if r.volume
            else 0,
            "active_users": r.active_users,
        }
        for r in results
    ]


# ==================== HEALTH ====================

@router.get("/health")
def get_admin_health_status(
    db: Session = Depends(get_db),
    admin=Depends(require_admin_user),
):

    db_status = "up"

    try:
        db.execute(text("SELECT 1"))

    except Exception:
        db_status = "down"

    status_value = (
        "healthy"
        if db_status == "up"
        else "degraded"
    )

    return {
        "status": status_value,
        "api": "up",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }