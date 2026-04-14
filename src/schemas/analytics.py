from pydantic import BaseModel
from typing import List, Optional

class AnalyticsResponse(BaseModel):
    total_sent: float
    total_received: float
    transaction_count: int
    unique_customers: Optional[int] = 0

class DailyAnalytics(BaseModel):
    date: str
    total_amount: float
    transaction_count: int

class TransactionTypeAnalytics(BaseModel):
    type: str
    amount: float
    count: int