"""Application settings loaded from environment variables."""

import os
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "APEX LINK"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    PORT: int = 8000  # Render sets this via PORT env var

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://apex_user:apex_password@postgres:5432/apex_link"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://apex_user:apex_password@postgres:5432/apex_link"
    DB_SSL: bool = True

    # Connection pool — conservative for free-tier managed PostgreSQL
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 300  # recycle connections every 5 minutes

    # JWT
    SECRET_KEY: str = "CHANGE_ME_BEFORE_PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # File storage
    STORAGE_MODE: str = "local"  # "local" or "s3"
    LOCAL_STORAGE_PATH: str = "./storage/evidence"

    # S3 (future)
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = "apex-link-evidence"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # AI
    AI_PROVIDER: str = "disabled"  # "disabled", "mock", "openai"
    OPENAI_API_KEY: str = ""

    # Rate limiting
    LOGIN_RATE_LIMIT: str = "5/minute"

    # Email verification
    EMAIL_PROVIDER: str = "console"  # "console" (dev), "demo" (public demo), "smtp" (production)
    VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 30
    VERIFICATION_RATE_LIMIT: int = 3  # max requests per 15 minutes
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@apex-link.local"

    # Login Challenge-Response
    CHALLENGE_EXPIRE_SECONDS: int = 120  # 2 minutes
    CHALLENGE_MAX_ATTEMPTS: int = 3

    # Legacy OTP (kept for backward compatibility)
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RATE_LIMIT: int = 3

    # Demo accounts
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    INVESTIGATOR_USERNAME: str = "investigator"
    INVESTIGATOR_PASSWORD: str = "investigator123"
    ANALYST_USERNAME: str = "analyst"
    ANALYST_PASSWORD: str = "analyst123"

    @field_validator("SECRET_KEY")
    @classmethod
    def reject_weak_secret(cls, v: str) -> str:
        """Reject obviously unsafe production secrets."""
        weak_secrets = {
            "CHANGE_ME_BEFORE_PRODUCTION",
            "change-me-to-a-random-secret-key-in-production",
            "change-me-to-a-random-secret-key",
            "secret",
            "changeme",
            "password",
        }
        is_prod = not os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
        if is_prod and v in weak_secrets:
            raise ValueError(
                "SECRET_KEY is insecure for production. "
                "Set a random SECRET_KEY (e.g. openssl rand -hex 32) via environment variable."
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()
