"""
Configuration management for API gateway.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    JWT_SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()

class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_VERSION: str = "v1"
    API_PORT: int = 8003
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database (for analytics data)
    DATABASE_URL: str = Field("sqlite:///./data/analytics.db", env="DATABASE_URL")
    
    # Service URLs
    AUTH_SERVICE_URL: str = Field("http://localhost:8007", env="AUTH_SERVICE_URL")
    TENANT_SERVICE_URL: str = Field("http://localhost:8004", env="TENANT_SERVICE_URL")
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from environment variable."""
        if isinstance(v, str):
            if v.startswith('[') and v.endswith(']'):
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()