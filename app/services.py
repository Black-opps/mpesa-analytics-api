from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import models   
from app.models import Transaction
from app.schemas import TransactionCreate, AnalyticsResponse


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
    transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == user_id)
        .all()
    )

    total_sent = sum(
        t.amount for t in transactions if t.transaction_type == "debit"
    )
    total_received = sum(
        t.amount for t in transactions if t.transaction_type == "credit"
    )

    return {
        "total_sent": total_sent,
        "total_received": total_received,
        "transaction_count": len(transactions),
    }
