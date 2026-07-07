# src/models/analytics_snapshot.py - HARDENED

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)

    # Aggregated metrics
    total_transactions = Column(Integer, default=0)
    unique_counterparties = Column(Integer, default=0)
    total_received = Column(Float, default=0.0)
    total_sent = Column(Float, default=0.0)
    net_flow = Column(Float, default=0.0)

    # Health scores
    health_score = Column(Integer, default=0)
    grade = Column(String, default="Poor")
    savings_rate = Column(Float, default=0.0)
    snapshot_version = Column(Integer, default=1)

    # Time ranges
    first_transaction_date = Column(DateTime)
    last_transaction_date = Column(DateTime)

    # Idempotency tracking
    last_upload_id = Column(String, nullable=True, index=True)
    last_imported_at = Column(DateTime)

    # Status
    is_stale = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_snapshot_tenant"),
        Index("idx_snapshot_tenant_status", "tenant_id", "is_stale"),
    )
