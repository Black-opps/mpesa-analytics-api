"""
Tenant context middleware for API gateway.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant context from JWT token.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Skip tenant context for public endpoints
        public_paths = ["/docs", "/redoc", "/openapi.json", "/health", "/", "/api/v1/auth"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Extract token
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            try:
                # Verify token with auth-service
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{settings.AUTH_SERVICE_URL}/api/v1/tokens/introspect",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        
                        # Store in request state
                        request.state.user = user_data
                        request.state.tenant_id = user_data.get("tenant_id")
                        request.state.user_id = user_data.get("sub")
                        request.state.user_role = user_data.get("role", "viewer")
                        
                        logger.debug(f"Tenant context: {request.state.tenant_id}")
                    else:
                        logger.warning(f"Token verification failed: {response.status_code}")
                        
            except Exception as e:
                logger.warning(f"Failed to extract tenant context: {e}")
        
        response = await call_next(request)
        return response
