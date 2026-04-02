"""
MPesa Analytics API Gateway
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .core.config import settings
from .routers import auth_proxy, admin, transactions, analytics
from .middleware.tenant_middleware import TenantContextMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MPesa Analytics API Gateway",
    description="Unified API Gateway for M-PESA Analytics Platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add tenant context middleware
app.add_middleware(TenantContextMiddleware)

# Include routers
app.include_router(auth_proxy.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "name": "MPesa Analytics API Gateway",
        "version": "2.0.0",
        "status": "operational",
        "services": {
            "auth": settings.AUTH_SERVICE_URL,
            "tenant": settings.TENANT_SERVICE_URL
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import httpx
    
    health_status = {
        "status": "healthy",
        "api": "operational",
        "services": {}
    }
    
    # Check auth service
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.AUTH_SERVICE_URL}/health", timeout=2)
            health_status["services"]["auth"] = "healthy" if resp.status_code == 200 else "unhealthy"
    except:
        health_status["services"]["auth"] = "unreachable"
        health_status["status"] = "degraded"
    
    return health_status
