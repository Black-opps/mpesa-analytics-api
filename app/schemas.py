from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: str
    
class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Transaction schemas
class TransactionBase(BaseModel):
    transaction_id: str
    amount: float
    transaction_type: str
    counterparty: str
    timestamp: datetime

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionCreate):
    id: int
    user_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Analytics schemas (if you have them)
class AnalyticsResponse(BaseModel):
    total_sent: int
    total_received: int
    transaction_count: int
   