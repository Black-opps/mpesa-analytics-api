from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from typing import Optional, List, Dict, Any
from app import models   
from app.models import Transaction, User
from app.schemas import TransactionCreate, AnalyticsResponse
from app.schemas.analytics import AnalyticsResponse



# Check your create_transactions function
def create_transactions(db: Session, transactions: list, user_id: int):
    inserted = 0
    skipped = 0
    
    for transaction in transactions:
        # DEBUG: Print what we're looking for
        print(f"Checking for transaction: {transaction.transaction_id}, user: {user_id}")
        
        existing = db.query(Transaction).filter(
            Transaction.transaction_id == transaction.transaction_id,
            # Make sure you're checking user_id if transactions are user-specific
            Transaction.user_id == user_id
        ).first()
        
        if existing:
            print(f"Transaction already exists! ID: {existing.id}")
            skipped += 1
        else:
            print(f"Creating new transaction")
            db_transaction = Transaction(
                transaction_id=transaction.transaction_id,
                amount=transaction.amount,
                transaction_type=transaction.transaction_type,
                counterparty=transaction.counterparty,
                timestamp=transaction.timestamp,
                user_id=user_id,
            )
            db.add(db_transaction)
            inserted += 1
    
    db.commit()
    print(f"Result: inserted={inserted}, skipped={skipped}")
    return {"inserted": inserted, "skipped": skipped}



def fetch_transactions(db: Session):
    return db.query(Transaction).all()


def compute_analytics(db: Session, user_id: int):
    """
    Compute analytics for a specific user
    Returns dict with total_sent, total_received, transaction_count
    """
    transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == user_id)
        .all()
    )

    # Based on your transaction types, determine which are "sent" vs "received"
    # Typically, send_money, pay_bill, buy_goods, withdraw are money going OUT (sent)
    # You might have receive_money for money coming IN (received)
    
    sent_types = ["send_money", "pay_bill", "buy_goods", "withdraw"]
    received_types = ["receive_money"]  # Add this if you have it
    
    total_sent = sum(
        t.amount for t in transactions if t.transaction_type in sent_types
    )
    
    total_received = sum(
        t.amount for t in transactions if t.transaction_type in received_types
    )
    
    # Calculate unique customers (unique counterparties)
    unique_customers = len(set(t.counterparty for t in transactions))

    return {
        "total_sent": total_sent,
        "total_received": total_received,
        "transaction_count": len(transactions),
        "unique_customers": unique_customers  # Add this for the dashboard
    }
# app/services.py - Add this helper function

def get_user_data_with_permission_check(
    db: Session, 
    current_user: User, 
    requested_user_id: Optional[int] = None
) -> int:
    """
    Helper function to determine which user_id to use based on permissions
    Regular users: always use their own ID
    Admins: can use requested_user_id or their own
    """
    if current_user.role == "admin" and requested_user_id is not None:
        # Admin can view any user's data
        return requested_user_id
    else:
        # Regular users can only view their own
        return current_user.id