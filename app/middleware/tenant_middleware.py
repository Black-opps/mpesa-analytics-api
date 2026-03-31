"""
Tenant context middleware for API gateway.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from ..services.auth_client import auth_client

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
                # Verify token and get user info
                user_data = await auth_client.verify_token(token)
                
                # Store in request state
                request.state.user = user_data
                request.state.tenant_id = user_data.get("tenant_id")
                request.state.user_id = user_data.get("sub")
                request.state.user_role = user_data.get("role", "viewer")
                
                logger.debug(f"Tenant context: {request.state.tenant_id}")
                
            except Exception as e:
                logger.warning(f"Failed to extract tenant context: {e}")
        
        response = await call_next(request)
        return response
