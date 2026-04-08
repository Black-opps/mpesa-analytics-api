# app/schemas/__init__.py

# Import user schemas
from app.schemas.user import UserCreate, UserResponse

# Import token schemas
from app.schemas.token import Token, TokenData

# Import transaction schemas
try:
    from app.schemas.transaction import TransactionCreate, TransactionResponse
except ImportError:
    TransactionCreate = None
    TransactionResponse = None
    print("Warning: Transaction schemas not found")

# Import analytics schemas
try:
    from app.schemas.analytics import AnalyticsResponse
except ImportError:
    AnalyticsResponse = None
    print("Warning: AnalyticsResponse schema not found")

# Export all schemas
__all__ = [
    "UserCreate",
    "UserResponse",
    "Token",
    "TokenData",
    "TransactionCreate",
    "TransactionResponse",
    "AnalyticsResponse",
]