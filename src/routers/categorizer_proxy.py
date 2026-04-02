"""
Categorizer proxy router - forwards requests to transaction-categorizer.
"""
from fastapi import APIRouter, Request, HTTPException, Response, Depends
import httpx
import logging

from ..core.config import settings
from ..core.dependencies import get_current_user, get_current_tenant_id

router = APIRouter(prefix="/categorize", tags=["Transaction Categorizer"])
logger = logging.getLogger(__name__)


@router.post("/")
async def categorize_transactions(
    request: Request,
    user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Categorize transactions.
    """
    url = f"{settings.CATEGORIZER_SERVICE_URL}/api/v1/categorize/"
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
        logger.error(f"Categorizer service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Categorizer service unavailable"
        )


@router.post("/single")
async def categorize_single(
    request: Request,
    user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Categorize a single transaction.
    """
    url = f"{settings.CATEGORIZER_SERVICE_URL}/api/v1/categorize/single"
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
        logger.error(f"Categorizer service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Categorizer service unavailable"
        )