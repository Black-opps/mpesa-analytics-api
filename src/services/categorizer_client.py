# src/services/categorizer_client.py - NEW FILE

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


class CategorizerClient:
    """Client for interacting with the Categorizer Service."""

    def __init__(self):
        self.base_url = os.getenv("CATEGORIZER_SERVICE_URL", "http://localhost:8009")
        self.timeout = 10.0

    async def get_counterparty_type(self, name: str, tenant_id: str) -> str:
        """
        Get counterparty type from Categorizer Service.
        Returns: "person", "business", "utility", or "unknown"
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/categorize/counterparty",
                    json={"name": name, "tenant_id": tenant_id},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("type", "unknown")
                else:
                    logger.warning(
                        f"Categorizer service returned {response.status_code}, using fallback"
                    )
                    return self._fallback_detect(name)

        except Exception as e:
            logger.error(f"Error calling categorizer service: {e}")
            return self._fallback_detect(name)

    @staticmethod
    def _fallback_detect(name: str) -> str:
        """Fallback detection if categorizer service is unavailable."""
        business_keywords = ["Ltd", "Limited", "Shop", "Mart", "Supermarket"]
        utility_keywords = ["Safaricom", "KPLC", "Water", "Internet", "Bill"]

        name_lower = name.lower()
        if any(k.lower() in name_lower for k in utility_keywords):
            return "utility"
        if any(k.lower() in name_lower for k in business_keywords):
            return "business"
        if name.startswith("07") or name.startswith("01") or name.startswith("+254"):
            return "person"
        return "unknown"


# Singleton
categorizer_client = CategorizerClient()
