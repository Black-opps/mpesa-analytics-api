from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String, unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, index=True)
    counterparty = Column(String)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    user = relationship("User", back_populates="transactions")


Index(
    "idx_user_type_timestamp",
    Transaction.user_id,
    Transaction.transaction_type,
    Transaction.timestamp,
)
