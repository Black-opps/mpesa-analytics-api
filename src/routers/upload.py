# src/routers/upload.py - HARDENED

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.dependencies import get_current_tenant_id, get_current_user
from src.models.transaction import Transaction
from src.models.upload_job import UploadJob, UploadStage
from src.workers.analytics_worker import refresh_tenant_analytics

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])


@router.post("/statement")
async def upload_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    password: str = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload M-PESA statement - async processing"""

    upload_id = f"upload_{tenant_id}_{int(datetime.utcnow().timestamp())}"

    # Create job
    job = UploadJob(
        tenant_id=tenant_id,
        upload_id=upload_id,
        file_name=file.filename,
        stage=UploadStage.PENDING,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    try:
        # Parse file
        parser = ParserService()
        transactions = await parser.parse_file(file, password)

        if not transactions:
            job.stage = UploadStage.FAILED
            job.error_message = "No transactions found"
            db.commit()
            raise HTTPException(status_code=400, detail="No transactions found")

        # Bulk insert with deduplication
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(Transaction).values(
            [
                {
                    "tenant_id": tenant_id,
                    "transaction_id": txn.get("transaction_id"),
                    "hash_key": txn.get("hash_key"),
                    "upload_id": upload_id,
                    "date": txn.get("date"),
                    "amount": float(txn.get("amount", 0)),
                    "transaction_type": txn.get("transaction_type"),
                    "counterparty": txn.get("counterparty", ""),
                    "category": txn.get("category", "Uncategorized"),
                    "description": txn.get("description", ""),
                    "created_at": datetime.utcnow(),
                }
                for txn in transactions
            ]
        )

        stmt = stmt.on_conflict_do_nothing(index_elements=["tenant_id", "hash_key"])

        result = db.execute(stmt)
        new_count = result.rowcount

        job.transactions_imported = new_count
        job.stage = UploadStage.IMPORTING
        db.commit()

        # Queue background analytics refresh
        refresh_tenant_analytics.send(tenant_id, upload_id)

        return {
            "status": "accepted",
            "upload_id": upload_id,
            "transactions_imported": new_count,
            "message": "Upload accepted. Analytics processing in background.",
            "status_url": f"/api/v1/uploads/{upload_id}/status",
        }

    except Exception as e:
        job.stage = UploadStage.FAILED
        job.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
