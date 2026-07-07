# mpesa-analytics-api/src/core/tenant_client.py - NEW

from typing import Any, Dict, Optional

import httpx
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class TenantClient:
    """Client for Tenant Service"""

    def __init__(self):
        self.base_url = settings.TENANT_SERVICE_URL  # http://localhost:8002
        self.timeout = 5.0

    async def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant details"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/tenants/{tenant_id}"
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get tenant: {e}")
            return None

    async def get_feature_flags(self, tenant_id: str) -> Dict[str, bool]:
        """Get feature flags for a tenant"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/features/{tenant_id}"
                )
                if response.status_code == 200:
                    return response.json()
                return {}
        except Exception as e:
            logger.error(f"Failed to get feature flags: {e}")
            return {}

    async def is_feature_enabled(self, tenant_id: str, feature: str) -> bool:
        """Check if a feature is enabled for a tenant"""
        flags = await self.get_feature_flags(tenant_id)
        return flags.get(feature, False)
