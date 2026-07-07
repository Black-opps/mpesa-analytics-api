# src/services/auth_client.py - FINAL OPTIMIZED VERSION

import logging
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status

from ..core.config import settings

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """Client for interacting with auth-service with optimized connection pooling."""

    def __init__(self):
        self.base_url = settings.AUTH_SERVICE_URL
        self.timeout = 10.0
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"🔐 Auth client configured with URL: {self.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create a shared HTTP client with optimized settings."""
        if self._client is None:
            logger.info("🔐 Creating optimized HTTP client")
            print("🔐 Creating optimized HTTP client")
            
            # ✅ OPTIMIZED: Use HTTP/1.1 with keep-alive, disable HTTP/2
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=2.0,      # Connection timeout
                    read=5.0,         # Read timeout
                    write=5.0,        # Write timeout
                    pool=2.0,         # Pool timeout
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=50,
                    keepalive_expiry=120.0,
                ),
                transport=httpx.AsyncHTTPTransport(
                    retries=1,
                    # ✅ Force HTTP/1.1, disable HTTP/2 (faster on localhost)
                    http2=False,
                ),
                # ✅ Disable automatic decompression for speed
                follow_redirects=False,
            )
        return self._client

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token with auth-service using optimized connection pooling.
        """
        url = f"{self.base_url}/api/v1/me"
        logger.info(f"🔐 Calling auth service: GET {url}")
        print(f"🔐 AUTH_HTTP_CALL START: {url}")

        try:
            client = await self._get_client()
            
            # ⏱️ Measure HTTP request
            http_start = time.perf_counter()
            response = await client.get(
                url, 
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Connection": "keep-alive",  # ✅ Explicit keep-alive
                }
            )
            http_elapsed = (time.perf_counter() - http_start) * 1000

            print(f"⏱️ AUTH_HTTP_REQUEST={http_elapsed:.2f}ms status={response.status_code}")
            logger.info(f"⏱️ AUTH_HTTP_REQUEST={http_elapsed:.2f}ms status={response.status_code}")

            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"✅ User verified: {user_data.get('email')}")
                return user_data
            else:
                error_detail = response.json().get("detail", "Invalid token")
                logger.warning(f"❌ Auth service returned {response.status_code}: {error_detail}")
                raise HTTPException(
                    status_code=response.status_code, detail=error_detail
                )

        except httpx.TimeoutException:
            elapsed = (time.perf_counter() - http_start) * 1000 if 'http_start' in locals() else 0
            logger.error(f"❌ Auth service timeout after {elapsed:.2f}ms")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable - timeout",
            )
        except httpx.ConnectError as e:
            elapsed = (time.perf_counter() - http_start) * 1000 if 'http_start' in locals() else 0
            logger.error(f"❌ Auth service connection failed after {elapsed:.2f}ms: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable - cannot connect",
            )
        except HTTPException:
            raise
        except Exception as e:
            elapsed = (time.perf_counter() - http_start) * 1000 if 'http_start' in locals() else 0
            logger.error(f"❌ Auth client error after {elapsed:.2f}ms: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("🔐 HTTP client closed")


# Singleton instance
auth_client = AuthServiceClient()