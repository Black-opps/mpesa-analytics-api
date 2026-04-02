"""
FastAPI dependencies for the API gateway.
"""
from fastapi import Depends, HTTPException, status, Request
from typing import Optional, Dict, Any
import logging

from ..services.auth_client import auth_client

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get current user from JWT token via auth-service.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    scheme, token = authorization.split()
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
        )
    
    try:
        user_data = await auth_client.verify_token(token)
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def get_current_tenant_id(user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Get current tenant ID from authenticated user.
    """
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to a tenant",
        )
    return tenant_id


def require_permission(permission: str):
    """
    Dependency factory for requiring specific permissions.
    """
    async def dependency(user: Dict[str, Any] = Depends(get_current_user)):
        user_permissions = user.get("permissions", [])
        user_role = user.get("role", "viewer")
        
        # Admin has all permissions
        if user_role == "admin":
            return user
        
        if permission not in user_permissions and "*" not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}",
            )
        return user
    return dependency