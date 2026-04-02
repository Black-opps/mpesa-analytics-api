"""
Analyzer proxy router - forwards requests to cashflow-analyzer.
"""
from fastapi import APIRouter, Request, HTTPException, Response, Depends
import httpx
import logging

from ..core.config import settings
from ..core.dependencies import get_current_user, get_current_tenant_id

router = APIRouter(prefix="/analytics", tags=["Cashflow Analytics"])
logger = logging.getLogger(__name__)


@router.get("/summary")
async def get_analytics_summary(
    request: Request,
    days: int = 30,
    user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get cashflow analytics summary.
    """
    url = f"{settings.ANALYZER_SERVICE_URL}/api/v1/cashflow/summary/{tenant_id}?days={days}"
    headers = dict(request.headers)
    headers.pop("host", None)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.RequestError as e:
        logger.error(f"Analyzer service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Analytics service unavailable"
        )


@router.post("/analyze")
async def analyze_cashflow(
    request: Request,
    user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Custom cashflow analysis.
    """
    url = f"{settings.ANALYZER_SERVICE_URL}/api/v1/cashflow/analyze"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["X-Tenant-ID"] = tenant_id
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method="POST",
                url=url,
                headers=headers,
                content=body,
                timeout=60.0
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.RequestError as e:
        logger.error(f"Analyzer service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Analytics service unavailable"
        )


@router.post("/patterns")
async def detect_patterns(
    request: Request,
    user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Detect cashflow patterns.
    """
    url = f"{settings.ANALYZER_SERVICE_URL}/api/v1/cashflow/patterns"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["X-Tenant-ID"] = tenant_id
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method="POST",
                url=url,
                headers=headers,
                content=body,
                timeout=30.0
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.RequestError as e:
        logger.error(f"Analyzer service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Analytics service unavailable"
        )