# src/core/config.py - COMPLETE WITH JWT SETTINGS

"""
Configuration management for API Gateway.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    API_VERSION: str = "v1"
    API_PORT: int = 8003
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Service URLs
    AUTH_SERVICE_URL: str = Field("http://127.0.0.1:8001", env="AUTH_SERVICE_URL")
    TENANT_SERVICE_URL: str = Field("http://localhost:8002", env="TENANT_SERVICE_URL")
    BILLING_SERVICE_URL: str = Field("http://localhost:8008", env="BILLING_SERVICE_URL")
    PAYMENT_SERVICE_URL: str = Field("http://localhost:8007", env="PAYMENT_SERVICE_URL")
    PARSER_SERVICE_URL: str = Field("http://localhost:8004", env="PARSER_SERVICE_URL")
    CATEGORIZER_SERVICE_URL: str = Field(
        "http://localhost:8009", env="CATEGORIZER_SERVICE_URL"
    )
    ANALYZER_SERVICE_URL: str = Field(
        "http://localhost:8010", env="ANALYZER_SERVICE_URL"
    )
    WEBHOOK_SERVICE_URL: str = Field("http://localhost:8011", env="WEBHOOK_SERVICE_URL")

    # ✅ JWT Settings - MATCH AUTH SERVICE (RS256)
    JWT_ALGORITHM: str = Field("RS256", env="JWT_ALGORITHM")
    JWKS_URL: str = Field("http://127.0.0.1:8001/.well-known/jwks.json", env="JWKS_URL")

    # Database
    DATABASE_URL: str = Field(
        "postgresql://postgres:Playee103@localhost:5432/transaction_db",
        env="DATABASE_URL",
    )

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8003",
        "http://localhost:9000",
    ]

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
