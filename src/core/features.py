# mpesa-analytics-api/src/core/features.py - NEW

from functools import wraps

from fastapi import HTTPException, Request
from src.core.tenant_client import TenantClient

tenant_client = TenantClient()


def require_feature(feature_name: str):
    """Decorator to require a feature flag"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise HTTPException(status_code=500, detail="Request not found")

            tenant_id = request.state.tenant_id
            if not tenant_id:
                raise HTTPException(status_code=403, detail="Tenant ID required")

            # Check feature flag
            enabled = await tenant_client.is_feature_enabled(tenant_id, feature_name)
            if not enabled:
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{feature_name}' is not enabled for this tenant",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
