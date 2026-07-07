# src/workers/analytics_worker.py - HARDENED

from datetime import datetime

import dramatiq
from src.core.database import SessionLocal
from src.core.exceptions import DuplicateUploadError
from src.core.logging import get_logger
from src.models.processed_upload import ProcessedUpload
from src.models.upload_job import UploadJob, UploadStage
from src.services.cache_service import CacheService
from src.services.lock_service import LockService
from src.services.metrics_service import MetricsService
from src.services.projection_service import ProjectionService

logger = get_logger(__name__)


@dramatiq.actor(max_retries=3, time_limit=300000, queue_name="analytics")
def refresh_tenant_analytics(tenant_id: str, upload_id: str = None):
    """Refresh analytics for a tenant - idempotent, locked, stage-tracked"""

    logger.info(
        f"🔄 Starting analytics refresh",
        extra={"tenant_id": tenant_id, "upload_id": upload_id},
    )

    # Acquire distributed lock
    lock_service = LockService()
    lock_key = f"analytics_refresh:{tenant_id}"

    with lock_service.with_lock(lock_key, timeout=300) as locked:
        if not locked:
            logger.warning(f"Could not acquire lock", extra={"tenant_id": tenant_id})
            return

        db = SessionLocal()
        try:
            # Check idempotency
            if upload_id:
                existing = (
                    db.query(ProcessedUpload)
                    .filter(ProcessedUpload.upload_id == upload_id)
                    .first()
                )

                if existing:
                    logger.info(
                        f"⏭️ Upload already processed", extra={"upload_id": upload_id}
                    )
                    return

            # Update job stage
            if upload_id:
                _update_job_stage(db, upload_id, UploadStage.ANALYTICS_REFRESHING)

            # Build projections
            projection_service = ProjectionService(db, tenant_id)
            snapshot = projection_service.refresh_snapshot(upload_id)

            # Mark as processed
            if upload_id:
                processed = ProcessedUpload(
                    upload_id=upload_id,
                    tenant_id=tenant_id,
                    processed_at=datetime.utcnow(),
                    transaction_count=snapshot.total_transactions,
                )
                db.add(processed)
                db.commit()

            # Update job to completed
            if upload_id:
                _update_job_stage(db, upload_id, UploadStage.COMPLETED)

            # Invalidate cache
            cache = CacheService()
            cache.invalidate_tenant_cache(tenant_id)

            # Track metrics
            MetricsService.set_health_score(tenant_id, snapshot.health_score)

            logger.info(
                f"✅ Analytics refresh complete",
                extra={"tenant_id": tenant_id, "upload_id": upload_id},
            )

        except Exception as e:
            logger.error(
                f"❌ Analytics refresh failed",
                extra={"tenant_id": tenant_id, "error": str(e)},
            )
            if upload_id:
                _update_job_stage(db, upload_id, UploadStage.FAILED, error=str(e))
            raise
        finally:
            db.close()


def _update_job_stage(db, upload_id: str, stage: UploadStage, error: str = None):
    """Update upload job stage"""
    if not upload_id:
        return

    job = db.query(UploadJob).filter(UploadJob.upload_id == upload_id).first()
    if job:
        job.stage = stage
        if stage == UploadStage.COMPLETED:
            job.completed_at = datetime.utcnow()
        elif stage == UploadStage.FAILED:
            job.failed_at = datetime.utcnow()
            if error:
                job.error_message = error
        db.commit()
