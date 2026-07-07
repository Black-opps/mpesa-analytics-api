# src/models/transaction.py

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Index, Numeric, String
from src.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    hash_key = Column(String, nullable=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    upload_file_id = Column(String, nullable=True, index=True)
    uploaded_by = Column(String, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    parser_version = Column(String, nullable=True)
    date = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    transaction_type = Column(String, nullable=False, index=True)
    counterparty = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    balance = Column(Numeric(18, 2), nullable=True)
    category = Column(String, nullable=True, index=True)
    merchant = Column(String, nullable=True, index=True)
    source = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
