# src/models/processed_upload.py - NEW

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base


class ProcessedUpload(Base):
    """Idempotency registry for uploads"""

    __tablename__ = "processed_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = Column(String, unique=True, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    transaction_count = Column(Integer, default=0)
    worker_id = Column(String, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("upload_id", name="uq_processed_upload"),
        Index("idx_processed_tenant", "tenant_id", "processed_at"),
    )
