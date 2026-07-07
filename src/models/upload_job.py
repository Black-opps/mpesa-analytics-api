# src/models/upload_job.py - HARDENED

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base


class UploadStage(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    IMPORTING = "importing"
    ANALYTICS_REFRESHING = "analytics_refreshing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadJob(Base):
    __tablename__ = "upload_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    upload_id = Column(String, unique=True, nullable=False, index=True)

    stage = Column(Enum(UploadStage), default=UploadStage.PENDING)

    file_name = Column(String)
    file_size = Column(Integer)

    transactions_imported = Column(Integer, default=0)
    transactions_failed = Column(Integer, default=0)

    worker_id = Column(String, nullable=True)
    attempt_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)
    last_heartbeat = Column(DateTime)

    error_message = Column(Text)
    error_stack = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_upload_tenant_stage", "tenant_id", "stage"),
        Index("idx_upload_tenant_created", "tenant_id", "created_at"),
    )
