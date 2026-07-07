# src/core/dependencies.py - COMPLETE WITH LOCAL JWT VALIDATION

import itertools
import logging
import time
from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from src.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

# ✅ Call counter for debugging
auth_counter = itertools.count(1)

# ✅ Local JWKS client for RS256 validation
_jwks_client = None


def get_jwks_client():
    """Get or create JWKS client for local JWT validation."""
    global _jwks_client
    if _jwks_client is None:
        try:
            _jwks_client = PyJWKClient(settings.JWKS_URL)
            logger.info(f"✅ JWKS client initialized with URL: {settings.JWKS_URL}")
            print(f"✅ JWKS client initialized with URL: {settings.JWKS_URL}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize JWKS client: {e}")
            raise
    return _jwks_client


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Get current user from JWT token - VALIDATED LOCALLY.
    No HTTP call to auth service!
    """
    call_id = next(auth_counter)
    start = time.perf_counter()
    token = credentials.credentials

    print(f"🔐 LOCAL_JWT_VALIDATION #{call_id} START")
    logger.info(f"🔐 LOCAL_JWT_VALIDATION #{call_id} START")

    try:
        # ✅ Validate JWT locally using RS256
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": True},
        )

        elapsed = (time.perf_counter() - start) * 1000
        print(f"🔐 LOCAL_JWT_VALIDATION #{call_id} END {elapsed:.2f}ms")
        logger.info(f"🔐 LOCAL_JWT_VALIDATION #{call_id} END {elapsed:.2f}ms")

        # Return user data from JWT payload
        return {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "tenant_id": payload.get("tenant_id"),
        }

    except jwt.ExpiredSignatureError:
        elapsed = (time.perf_counter() - start) * 1000
        logger.error(f"❌ Token expired after {elapsed:.2f}ms")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError as e:
        elapsed = (time.perf_counter() - start) * 1000
        logger.error(f"❌ Invalid token after {elapsed:.2f}ms: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        logger.error(f"❌ Authentication error after {elapsed:.2f}ms: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def get_current_tenant_id(
    user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    """
    Get current tenant ID from authenticated user.
    """
    start = time.perf_counter()
    tenant_id = user.get("tenant_id")
    elapsed = (time.perf_counter() - start) * 1000
    print(f"⏱️ TENANT_ID={elapsed:.2f}ms")
    logger.info(f"⏱️ TENANT_ID={elapsed:.2f}ms")

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to a tenant",
        )
    return tenant_id
