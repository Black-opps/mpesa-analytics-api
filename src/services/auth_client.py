"""
HTTP client for auth-service.
"""
import httpx
from fastapi import HTTPException, status
from typing import Dict, Any
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """Client for interacting with auth-service."""
    
    def __init__(self):
        self.base_url = settings.AUTH_SERVICE_URL
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token with auth-service."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/tokens/introspect",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                logger.warning(f"Token verification failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Auth service connection error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )


auth_client = AuthServiceClient()