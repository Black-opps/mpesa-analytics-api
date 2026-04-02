"""
Routers for API Gateway.
"""
from .auth_proxy import router as auth_router
from .tenant_proxy import router as tenant_router
from .billing_proxy import router as billing_router
from .payment_proxy import router as payment_router
from .parser_proxy import router as parser_router
from .categorizer_proxy import router as categorizer_router
from .analyzer_proxy import router as analyzer_router
from .webhook_proxy import router as webhook_router

__all__ = [
    "auth_router",
    "tenant_router",
    "billing_router",
    "payment_router",
    "parser_router",
    "categorizer_router",
    "analyzer_router",
    "webhook_router",
]