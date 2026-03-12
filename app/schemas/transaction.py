# app/schemas/transaction.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransactionBase(BaseModel):
    transaction_id: str
    amount: float
    transaction_type: str
    counterparty: str
    timestamp: datetime

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True