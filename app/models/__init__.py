# app/models/__init__.py

from app.models.user import User
from app.models.transaction import Transaction  # Note: 'transaction' not 'transactions'

__all__ = ["User", "Transaction"]