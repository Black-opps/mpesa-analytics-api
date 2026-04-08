from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.transaction import Transaction

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


@router.get("/")
def get_transactions(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).limit(50).all()

    return transactions