# app/api/endpoints/analytics.py - COMPLETE FIXED VERSION

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.analytics import (
    AnalyticsResponse,
    DailyAnalyticsResponse,
    TransactionTypeResponse,
    TopCustomerResponse
)

router = APIRouter()

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get main analytics summary"""
    
    # Get all transactions for current user
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    
    # Calculate analytics
    total_sent = sum(t.amount for t in transactions)
    total_received = 0  # You can calculate this based on your business logic
    transaction_count = len(transactions)
    
    return AnalyticsResponse(
        total_sent=total_sent,
        total_received=total_received,
        transaction_count=transaction_count
    )

@router.get("/analytics/daily", response_model=List[DailyAnalyticsResponse])
async def get_daily_analytics(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get daily transaction totals"""
    start_date = datetime.now() - timedelta(days=days)
    
    results = db.query(
        func.date(Transaction.timestamp).label('date'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.timestamp >= start_date
    ).group_by(
        func.date(Transaction.timestamp)
    ).order_by(
        func.date(Transaction.timestamp)
    ).all()
    
    return [
        DailyAnalyticsResponse(
            date=str(r.date),
            amount=float(r.total) if r.total else 0
        ) for r in results
    ]

@router.get("/analytics/transaction-types", response_model=List[TransactionTypeResponse])
async def get_transaction_type_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get transaction breakdown by type"""
    results = db.query(
        Transaction.transaction_type,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == current_user.id
    ).group_by(
        Transaction.transaction_type
    ).all()
    
    return [
        TransactionTypeResponse(
            type=r.transaction_type,
            amount=float(r.total) if r.total else 0,
            count=r.count
        ) for r in results
    ]

@router.get("/analytics/top-customers", response_model=List[TopCustomerResponse])
async def get_top_customers(
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top customers by transaction volume"""
    results = db.query(
        Transaction.counterparty,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == current_user.id
    ).group_by(
        Transaction.counterparty
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(limit).all()
    
    return [
        TopCustomerResponse(
            counterparty=r.counterparty,
            total=float(r.total) if r.total else 0,
            count=r.count
        ) for r in results
    ]