"""
Payment proxy router - forwards requests to payment-service.
"""
from fastapi import APIRouter, Request, HTTPException, Response, Depends
import httpx
import logging

from ..core.config import settings
from ..core.dependencies import get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_payment(request: Request, path: str, user: dict = Depends(get_current_user)):
    """
    Proxy all payment requests to payment-service.
    """
    url = f"{settings.PAYMENT_SERVICE_URL}/api/v1/{path}"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
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
        logger.error(f"Payment service proxy error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Payment service unavailable"
        )