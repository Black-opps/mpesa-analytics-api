# app/routers/transactions.py - CREATE THIS FILE

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Transaction, User
from app import schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("/", response_model=List[schemas.TransactionResponse])
@router.get("", response_model=List[schemas.TransactionResponse])  # Add this line
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    show_all: bool = Query(False, description="Admin only: show all transactions")
):
    """
    Get transactions with optional filters.
    
    - Regular users: See only their own transactions
    - Admin users: Can see all transactions by setting show_all=True
    """
    try:
        # Base query - start with user filter for security
        query = db.query(Transaction)
        
        # Admin override
        if current_user.role == "admin" and show_all:
            logger.info(f"Admin {current_user.id} viewing all transactions")
            # No filter - see all
        else:
            # Regular user sees only their own
            query = query.filter(Transaction.user_id == current_user.id)
        
        # Apply optional filters
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        if start_date:
            query = query.filter(Transaction.timestamp >= start_date)
        if end_date:
            query = query.filter(Transaction.timestamp <= end_date)
        
        # Apply pagination and ordering
        transactions = query.order_by(Transaction.timestamp.desc()).offset(skip).limit(limit).all()
        
        logger.info(f"Retrieved {len(transactions)} transactions for user {current_user.id}")
        return transactions
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch transactions"
        )

@router.get("/{transaction_id}", response_model=schemas.TransactionResponse)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific transaction by ID"""
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Check permissions
    if transaction.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this transaction"
        )
    
    return transaction

@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a transaction - users can only delete their own, admins can delete any"""
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Check permissions
    if transaction.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this transaction"
        )
    
    try:
        db.delete(transaction)
        db.commit()
        logger.info(f"Transaction {transaction_id} deleted by user {current_user.id}")
        return {"message": "Transaction deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete transaction"
        )