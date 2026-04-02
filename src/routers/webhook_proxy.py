"""
Webhook proxy router - forwards requests to webhook-service.
"""
from fastapi import APIRouter, Request, HTTPException, Response, Depends
import httpx
import logging

from ..core.config import settings
from ..core.dependencies import get_current_user, get_current_tenant_id

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)


@router.get("/endpoints")
async def list_webhooks(
    request: Request,
    user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    List webhook endpoints.
    """
    url = f"{settings.WEBHOOK_SERVICE_URL}/api/v1/endpoints/"
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["X-Tenant-ID"] = tenant_id
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.RequestError as e:
        logger.error(f"Webhook service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Webhook service unavailable"
        )


@router.post("/endpoints")
async def create_webhook(
    request: Request,
    user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Create a webhook endpoint.
    """
    url = f"{settings.WEBHOOK_SERVICE_URL}/api/v1/endpoints/"
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
        logger.error(f"Webhook service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Webhook service unavailable"
        )