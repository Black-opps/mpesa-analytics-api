from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.routers import auth, users
from app.database import get_db, engine, Base
from app import schemas, services, models
from app.auth import get_current_user

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MPesa Analytics API",
    version="0.2.1",
)

# -------------------------
# Health Check
# -------------------------
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "MPesa Analytics API",
        "version": "0.2.1",
    }

# -------------------------
# Transactions
# -------------------------
@app.post("/transactions")
def ingest_transactions(
    transactions: list[schemas.TransactionCreate],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # FIXED: Removed duplicate call to create_transactions
    result = services.create_transactions(
        db=db,
        transactions=transactions,
        user_id=current_user.id,
    )
    return result


@app.get("/analytics", response_model=schemas.AnalyticsResponse)
def analytics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return services.compute_analytics(
        db=db,
        user_id=current_user.id,
    )

# -------------------------
# Routers
# -------------------------
app.include_router(auth.router)
app.include_router(users.router)        