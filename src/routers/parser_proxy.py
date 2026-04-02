"""
Parser proxy router - forwards requests to transaction-parser.
"""
from fastapi import APIRouter, Request, HTTPException, Response, Depends
import httpx
import logging

from ..core.config import settings
from ..core.dependencies import get_current_user, get_current_tenant_id

router = APIRouter(prefix="/parser", tags=["Transaction Parser"])
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_statement(
    request: Request,
    user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Upload M-PESA statement for parsing.
    """
    url = f"{settings.PARSER_SERVICE_URL}/api/v1/parse"
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
        logger.error(f"Parser service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Parser service unavailable"
        )