"""
MPesa Analytics API - Pure Analytics Service
All analytics endpoints are now in routers/analytics.py
"""
from jose import jwt
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from src.core.database import get_db
from src.routers import analytics

load_dotenv()

app = FastAPI(
    title="Analytics Service", 
    version="1.0.0",
    description="M-Pesa Analytics Service - Multi-tenant transaction analytics",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - Allow gateway and frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000", "http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Health & Debug Endpoints ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "analytics-service", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Analytics Service", 
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "analytics": "/api/v1/analytics/summary"
        }
    }

@app.get("/api/v1/auth/debug-token")
async def debug_token(request: Request):
    """Debug endpoint to check token validation"""
    auth_header = request.headers.get("Authorization")
    
    result = {"auth_header_received": auth_header is not None}
    
    if auth_header:
        token = auth_header.replace("Bearer ", "")
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            result["unverified_payload"] = unverified
            SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "your-secret-key"))
            verified = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            result["verified_payload"] = verified
            result["validation"] = "SUCCESS"
        except Exception as e:
            result["error"] = str(e)
    
    return result

@app.get("/api/v1/analytics/test-no-auth")
async def test_no_auth(db: Session = Depends(get_db)):
    """Test endpoint without authentication (for debugging)"""
    from src.core.database import get_db
    from src.models import Transaction
    count = db.query(Transaction).count()
    return {"total_transactions_in_db": count}

# ==================== Include Analytics Router ====================
# All analytics endpoints are now in the router
app.include_router(analytics.router)

# Note: The following endpoints have been moved to routers/analytics.py:
# - GET /api/v1/analytics/summary
# - GET /api/v1/analytics/customers  
# - GET /api/v1/analytics/insights
# - GET /api/v1/analytics/daily
# - GET /api/v1/analytics/transaction-types
# - GET /api/v1/analytics/top-customers
# - GET /api/v1/analytics/transactions

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)