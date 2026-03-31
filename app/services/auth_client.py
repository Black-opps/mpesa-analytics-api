"""
HTTP client for auth-service.
"""
import httpx
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
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
        """
        Verify JWT token with auth-service.
        
        Args:
            token: JWT token from request
            
        Returns:
            Token payload with user info
            
        Raises:
            HTTPException: If token invalid
        """
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
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user via auth-service.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Login response with tokens
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": email, "password": password}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", "Login failed")
                )
            
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Auth service connection error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Auth service error: {e}")
            raise HTTPException(status_code=503, detail="Auth service unavailable")
    
    async def logout(self, token: str, refresh_token: Optional[str] = None):
        """Logout user."""
        try:
            await self.client.post(
                f"{self.base_url}/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                json={"refresh_token": refresh_token}
            )
        except httpx.RequestError as e:
            logger.error(f"Auth service error: {e}")
            # Don't raise - logout is best effort


# Singleton instance
auth_client = AuthServiceClient()
