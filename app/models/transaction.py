# app/models/transaction.py

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False, index=True)
    counterparty = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationship with user
    user = relationship("User", back_populates="transactions")

# Composite index for efficient queries
Index(
    "idx_user_type_timestamp",
    Transaction.user_id,
    Transaction.transaction_type,
    Transaction.timestamp,
)