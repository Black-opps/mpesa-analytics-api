# app/schemas/analytics.py - CREATE THIS FILE

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AnalyticsResponse(BaseModel):
    total_sent: float
    total_received: float
    transaction_count: int
    unique_customers: int = 0  # Add this field with default

    
    class Config:
        from_attributes = True

class DailyAnalyticsResponse(BaseModel):
    date: str
    amount: float
    count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class TransactionTypeResponse(BaseModel):
    type: str
    amount: float
    count: int
    
    class Config:
        from_attributes = True

class TopCustomerResponse(BaseModel):
    counterparty: str
    total: float
    count: int
    
    class Config:
        from_attributes = True