"""
MPesa Analytics API Gateway - Main entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .core.config import settings
from .routers import (
    auth_router,
    tenant_router,
    billing_router,
    payment_router,
    parser_router,
    categorizer_router,
    analyzer_router,
    webhook_router,
)
from .middleware.tenant_middleware import TenantContextMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="M-PESA Analytics API Gateway",
    description="Unified API Gateway for 10-Microservice M-PESA SaaS Platform",
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

# Include all routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenant_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(payment_router, prefix="/api/v1")
app.include_router(parser_router, prefix="/api/v1")
app.include_router(categorizer_router, prefix="/api/v1")
app.include_router(analyzer_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "name": "M-PESA Analytics API Gateway",
        "version": "2.0.0",
        "status": "operational",
        "services": {
            "auth": settings.AUTH_SERVICE_URL,
            "tenant": settings.TENANT_SERVICE_URL,
            "billing": settings.BILLING_SERVICE_URL,
            "payment": settings.PAYMENT_SERVICE_URL,
            "parser": settings.PARSER_SERVICE_URL,
            "categorizer": settings.CATEGORIZER_SERVICE_URL,
            "analyzer": settings.ANALYZER_SERVICE_URL,
            "webhook": settings.WEBHOOK_SERVICE_URL,
        },
        "endpoints": {
            "auth": "/api/v1/auth",
            "tenants": "/api/v1/tenants",
            "billing": "/api/v1/billing",
            "payments": "/api/v1/payments",
            "parser": "/api/v1/parser",
            "categorizer": "/api/v1/categorize",
            "analytics": "/api/v1/analytics",
            "webhooks": "/api/v1/webhooks",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import httpx
    
    health_status = {
        "status": "healthy",
        "gateway": "operational",
        "services": {}
    }
    
    # Check each service
    services = {
        "auth": settings.AUTH_SERVICE_URL,
        "tenant": settings.TENANT_SERVICE_URL,
        "billing": settings.BILLING_SERVICE_URL,
        "payment": settings.PAYMENT_SERVICE_URL,
        "parser": settings.PARSER_SERVICE_URL,
        "categorizer": settings.CATEGORIZER_SERVICE_URL,
        "analyzer": settings.ANALYZER_SERVICE_URL,
        "webhook": settings.WEBHOOK_SERVICE_URL,
    }
    
    for name, url in services.items():
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{url}/health", timeout=2)
                health_status["services"][name] = "healthy" if resp.status_code == 200 else "unhealthy"
        except:
            health_status["services"][name] = "unreachable"
            health_status["status"] = "degraded"
    
    return health_status