# src/core/database.py - COMPLETE WITH DB SESSION TIMING

import logging
import os
import time
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:Playee103@localhost:5432/transaction_db"
)

# Configure engine based on database type
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Transaction(Base):
    """Transaction model for analytics - MATCHES DATABASE SCHEMA"""

    __tablename__ = "transactions"
    __table_args__ = (
        # ✅ COMPOSITE INDEXES FOR COMMON QUERY PATTERNS
        Index("idx_transactions_tenant_type", "tenant_id", "transaction_type"),
        Index("idx_transactions_tenant_counterparty", "tenant_id", "counterparty"),
        Index("idx_transactions_tenant_date", "tenant_id", "date"),
        Index(
            "idx_transactions_tenant_type_date", "tenant_id", "transaction_type", "date"
        ),
        Index(
            "idx_transactions_tenant_counterparty_type",
            "tenant_id",
            "counterparty",
            "transaction_type",
        ),
        {"extend_existing": True},
    )

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

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "transaction_id": self.transaction_id,
            "date": self.date.isoformat() if self.date else None,
            "amount": float(self.amount),
            "transaction_type": self.transaction_type,
            "counterparty": self.counterparty,
            "category": self.category,
            "description": self.description,
        }


class TransactionSummary(Base):
    """Pre-aggregated summary for quick dashboard queries"""

    __tablename__ = "transaction_summaries"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    period = Column(String)  # "daily", "weekly", "monthly", "yearly"
    date = Column(DateTime, nullable=False)
    total_sent = Column(Float, default=0.0)
    total_received = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class CategoryStats(Base):
    """Category statistics for analytics"""

    __tablename__ = "category_stats"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    category = Column(String, nullable=False)
    total_amount = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Database Functions ====================


def get_db():
    """Dependency for FastAPI endpoints - yields a database session with timing"""
    start = time.perf_counter()
    db = SessionLocal()
    elapsed = (time.perf_counter() - start) * 1000
    print(f"⏱️ DB_SESSION_CREATE={elapsed:.2f}ms")
    logger.info(f"⏱️ DB_SESSION_CREATE={elapsed:.2f}ms")
    try:
        yield db
    finally:
        close_start = time.perf_counter()
        db.close()
        close_elapsed = (time.perf_counter() - close_start) * 1000
        print(f"⏱️ DB_SESSION_CLOSE={close_elapsed:.2f}ms")


def init_db():
    """Initialize database - creates all tables"""
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created")


def drop_db():
    """Drop all tables (for testing)"""
    Base.metadata.drop_all(bind=engine)
    print("[WARN] Database tables dropped")


def get_transaction_stats(db, tenant_id: str):
    """Get transaction statistics for a tenant"""
    from sqlalchemy import func

    total_sent = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.tenant_id == tenant_id, Transaction.transaction_type == "sent"
        )
        .scalar()
        or 0.0
    )

    total_received = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type == "received",
        )
        .scalar()
        or 0.0
    )

    total_transactions = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.tenant_id == tenant_id)
        .scalar()
        or 0
    )

    average_transaction = (
        (total_received - abs(total_sent)) / total_transactions
        if total_transactions > 0
        else 0
    )

    return {
        "total_transactions": total_transactions,
        "total_sent": abs(float(total_sent)),
        "total_received": float(total_received),
        "total_amount": float(total_received - abs(total_sent)),
        "average_transaction": float(average_transaction),
        "active_days": 0,
    }


def get_category_breakdown(db, tenant_id: str):
    """Get spending breakdown by category"""
    from sqlalchemy import func

    results = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .filter(
            Transaction.tenant_id == tenant_id, Transaction.transaction_type == "sent"
        )
        .group_by(Transaction.category)
        .all()
    )

    total = sum(abs(r.total) for r in results) if results else 0

    return [
        {
            "category": r.category or "Uncategorized",
            "amount": abs(float(r.total)),
            "count": r.count,
            "percentage": round(
                (abs(float(r.total)) / total * 100) if total > 0 else 0, 1
            ),
        }
        for r in results
    ]


# Auto-initialize when imported
print(f"🔧 Database URL: {DATABASE_URL}")
init_db()


# Export for use in other modules
__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "Transaction",
    "TransactionSummary",
    "CategoryStats",
    "init_db",
    "drop_db",
    "get_transaction_stats",
    "get_category_breakdown",
]
