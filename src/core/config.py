"""
Configuration management for API Gateway.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_VERSION: str = "v1"
    API_PORT: int = 8003
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Service URLs (all 10 microservices)
    AUTH_SERVICE_URL: str = Field("http://localhost:8007", env="AUTH_SERVICE_URL")
    TENANT_SERVICE_URL: str = Field("http://localhost:8004", env="TENANT_SERVICE_URL")
    BILLING_SERVICE_URL: str = Field("http://localhost:8005", env="BILLING_SERVICE_URL")
    PAYMENT_SERVICE_URL: str = Field("http://localhost:8006", env="PAYMENT_SERVICE_URL")
    PARSER_SERVICE_URL: str = Field("http://localhost:8000", env="PARSER_SERVICE_URL")
    CATEGORIZER_SERVICE_URL: str = Field("http://localhost:8001", env="CATEGORIZER_SERVICE_URL")
    ANALYZER_SERVICE_URL: str = Field("http://localhost:8002", env="ANALYZER_SERVICE_URL")
    WEBHOOK_SERVICE_URL: str = Field("http://localhost:8008", env="WEBHOOK_SERVICE_URL")
    
    # Database (for analytics data only)
    DATABASE_URL: str = Field("sqlite:///./analytics.db", env="DATABASE_URL")
    
    # CORS - Hardcoded (not from env)
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8003"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()