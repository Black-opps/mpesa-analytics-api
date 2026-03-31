# app/main.py - COMPLETE CLEANED VERSION

from fastapi import FastAPI
from .middleware.tenant_middleware import TenantContextMiddleware, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func
from typing import Optional, List
import logging
import uvicorn
from sqlalchemy import text

from app.routers import auth, users, admin, transactions
from app.core.database import get_db, engine, Base
from app import schemas, services
from app.core.security import get_current_user
from app.models import Transaction, User
from app.schemas import TransactionCreate


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

app = FastAPI(
    title="MPesa Analytics API",
    version="0.2.1",
    description="API for MPesa transaction analytics",
    contact={
        "name": "API Support",
        "email": "support@mpesa-analytics.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Add middleware AFTER app is created
#from starlette.middleware.base import BaseHTTPMiddleware
#from starlette.requests import Request
#from starlette.responses import RedirectResponse

#class TrailingSlashMiddleware(BaseHTTPMiddleware):
#    async def dispatch(self, request: Request, call_next):
 #       path = request.url.path
        # If path doesn't end with slash and isn't a file extension and isn't the root
   #     if not path.endswith('/') and '.' not in path.split('/')[-1] and path != '/':
            # Redirect to URL with trailing slash
  #          return RedirectResponse(url=path + '/', status_code=307)
 #       return await call_next(request)

# Add the trailing slash middleware
#app.add_middleware(TrailingSlashMiddleware)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

class TrailingSlashMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip auth routes to prevent redirect loops
        if path.startswith('/auth/'):
            return await call_next(request)
            
        # If path doesn't end with slash and isn't a file extension and isn't the root
        if not path.endswith('/') and '.' not in path.split('/')[-1] and path != '/':
            return RedirectResponse(url=path + '/', status_code=307)
        return await call_next(request)

# Configure CORS with more options
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# -------------------------
# Middleware for request logging
# -------------------------
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests"""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    formatted_process_time = f"{process_time:.2f}ms"
    
    # Log response
    logger.info(f"Response: {response.status_code} - {formatted_process_time}")
    
    # Add processing time header
    response.headers["X-Process-Time"] = formatted_process_time
    
    return response

# -------------------------
# Root & Health Endpoints
# -------------------------
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "status": "ok",
        "service": "MPesa Analytics API",
        "version": app.version,
        "description": app.description,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "up",
            "database": "unknown"
        }
    }
    
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "up"
    except Exception as e:
        health_status["services"]["database"] = "down"
        health_status["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")
    
    return health_status

# -------------------------
# Customer Endpoints
# -------------------------
@app.get("/customers")
def get_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Get all customers (counterparties) for the current user"""
    
    customers = db.query(
        Transaction.counterparty,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(Transaction.amount).label('total_volume'),
        func.max(Transaction.timestamp).label('last_transaction'),
        func.avg(Transaction.amount).label('average_transaction')
    ).filter(
        Transaction.user_id == current_user.id
    ).group_by(
        Transaction.counterparty
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "id": c.counterparty,
            "phone": c.counterparty,
            "transaction_count": c.transaction_count,
            "total_volume": float(c.total_volume) if c.total_volume else 0,
            "average_transaction": float(c.average_transaction) if c.average_transaction else 0,
            "last_transaction": c.last_transaction.isoformat() if c.last_transaction else None,
            "first_name": f"Customer {c.counterparty[-4:]}",
        } for c in customers
    ]

# -------------------------
# Transaction Endpoints
# -------------------------
@app.post("/transactions", 
          response_model=dict,
          status_code=status.HTTP_201_CREATED,
          summary="Create multiple transactions",
          description="Ingest multiple MPesa transactions for the current user")
def ingest_transactions(
    transactions: List[TransactionCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingest multiple MPesa transactions"""
    try:
        logger.info(f"User {current_user.id} attempting to create {len(transactions)} transactions")
        
        result = services.create_transactions(
            db=db,
            transactions=transactions,
            user_id=current_user.id,
        )
        
        logger.info(f"Successfully created {result['created_count']} transactions for user {current_user.id}")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=result
        )
    except Exception as e:
        logger.error(f"Error creating transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transactions: {str(e)}"
        )

# -------------------------
# Analytics Endpoints
# -------------------------
@app.get("/analytics", response_model=schemas.AnalyticsResponse)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analytics summary for the current user"""
    try:
        analytics = services.compute_analytics(
            db=db,
            user_id=current_user.id,
        )
        logger.info(f"Analytics computed for user {current_user.id}")
        return analytics
    except Exception as e:
        logger.error(f"Error computing analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute analytics"
        )

@app.get("/analytics/transaction-types")
def get_transaction_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transaction breakdown by type for the current user"""
    results = db.query(
        Transaction.transaction_type,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == current_user.id
    ).group_by(
        Transaction.transaction_type
    ).all()
    
    return [
        {
            "type": r.transaction_type,
            "amount": float(r.total) if r.total else 0,
            "count": r.count
        } for r in results
    ]

@app.get("/analytics/daily")
def get_daily_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get daily transaction totals for the last N days"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        results = db.query(
            func.date(Transaction.timestamp).label('date'),
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).filter(
            Transaction.user_id == current_user.id,
            Transaction.timestamp >= start_date
        ).group_by(
            func.date(Transaction.timestamp)
        ).order_by(
            func.date(Transaction.timestamp)
        ).all()
        
        return [
            {
                "date": str(r.date),
                "amount": float(r.total) if r.total else 0,
                "count": r.count
            } for r in results
        ]
    except Exception as e:
        logger.error(f"Error computing daily analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute daily analytics"
        )

@app.get("/analytics/top-customers")
def get_top_customers_endpoint(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top customers by transaction volume"""
    from sqlalchemy import func
    
    # Get real data from database
    results = db.query(
        Transaction.counterparty,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == current_user.id
    ).group_by(
        Transaction.counterparty
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(limit).all()
    
    # If we have real data, use it
    if results:
        return [
            {
                "id": str(i + 1),
                "name": f"Customer {r.counterparty[-4:]}",
                "transactions": r.count,
                "volume": float(r.total) if r.total else 0,
                "trend": 12.5
            } for i, r in enumerate(results)
        ]
    else:
        # Fallback to mock data
        return [
            {
                "id": "1",
                "name": "John Doe",
                "transactions": 145,
                "volume": 125000,
                "trend": 12.5
            },
            {
                "id": "2",
                "name": "Jane Smith",
                "transactions": 98,
                "volume": 89000,
                "trend": 8.2
            }
        ]

@app.get("/analytics/summary")
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a comprehensive analytics summary"""
    try:
        # Get basic analytics
        basic = services.compute_analytics(db, current_user.id)
        
        # Get transaction types
        types = db.query(
            Transaction.transaction_type,
            func.count(Transaction.id).label('count')
        ).filter(
            Transaction.user_id == current_user.id
        ).group_by(
            Transaction.transaction_type
        ).all()
        
        # Get recent activity
        recent = db.query(Transaction).filter(
            Transaction.user_id == current_user.id
        ).order_by(
            Transaction.timestamp.desc()
        ).limit(5).all()
        
        return {
            "summary": basic.dict() if hasattr(basic, 'dict') else basic,
            "transaction_types": [{"type": t.transaction_type, "count": t.count} for t in types],
            "recent_transactions": recent,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error computing analytics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute analytics summary"
        )

@app.get("/analytics/customer-segments")
def get_customer_segments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get customer segments (mock data for now)"""
    return [
        {
            "id": "1",
            "name": "High Value",
            "value": 45,
            "percentage": 45,
            "color": "#6366f1"
        },
        {
            "id": "2",
            "name": "Medium Value",
            "value": 30,
            "percentage": 30,
            "color": "#10b981"
        },
        {
            "id": "3",
            "name": "Low Value",
            "value": 15,
            "percentage": 15,
            "color": "#f59e0b"
        },
        {
            "id": "4",
            "name": "Inactive",
            "value": 10,
            "percentage": 10,
            "color": "#ec4899"
        }
    ]

# -------------------------
# User Endpoints
# -------------------------
@app.get("/users/me", response_model=schemas.UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@app.get("/users/me/statistics")
def get_user_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user statistics"""
    total_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).count()
    
    total_volume = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id
    ).scalar() or 0
    
    first_transaction = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.timestamp).first()
    
    last_transaction = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.timestamp.desc()).first()
    
    return {
        "total_transactions": total_transactions,
        "total_volume": float(total_volume),
        "average_transaction": float(total_volume / total_transactions) if total_transactions > 0 else 0,
        "first_transaction_date": first_transaction.timestamp.isoformat() if first_transaction else None,
        "last_transaction_date": last_transaction.timestamp.isoformat() if last_transaction else None,
        "account_created": current_user.created_at.isoformat()
    }

# -------------------------
# Include Routers
# -------------------------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(transactions.router)

# -------------------------
# Exception Handlers
# -------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# -------------------------
# Startup and Shutdown Events
# -------------------------
@app.on_event("startup")
async def startup_event():
    """Actions to run on application startup"""
    logger.info("Starting up MPesa Analytics API...")

@app.on_event("shutdown")
async def shutdown_event():
    """Actions to run on application shutdown"""
    logger.info("Shutting down MPesa Analytics API...")

# -------------------------
# Run the application
# -------------------------
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
