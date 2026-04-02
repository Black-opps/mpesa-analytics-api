"""
Auth proxy router - forwards auth requests to auth-service.
"""
from fastapi import APIRouter, Request, HTTPException, Response
import httpx
import logging

from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_auth(request: Request, path: str):
    """
    Proxy all auth requests to auth-service.
    """
    # Forward the request to auth-service
    url = f"{settings.AUTH_SERVICE_URL}/api/v1/auth/{path}"
    
    # Get the request body
    body = await request.body()
    
    # Forward headers (excluding host)
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
            
            # Return the response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.RequestError as e:
        logger.error(f"Auth service proxy error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable"
        )
