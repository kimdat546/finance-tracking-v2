"""Application configuration using Pydantic Settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "Finance Tracker Backend"
    APP_ENV: str = Field(default="dev", pattern="^(dev|staging|prod)$")
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(default="change-this-in-production")
    ALGORITHM: str = Field(default="HS256")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost/finance_db"
    )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Gmail Integration
    GMAIL_CREDENTIALS_PATH: str = Field(default="credentials.json")
    GMAIL_TOKEN_PATH: str = Field(default="token.json")
    EMAIL_SYNC_INTERVAL_MINUTES: int = Field(default=15, ge=1)

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # Backup
    BACKUP_DIR: str = Field(default="/var/backups/finance-tracker")

    # API Configuration
    API_TITLE: str = "Finance Tracker API"
    API_VERSION: str = "0.1.0"
    API_DESCRIPTION: str = "Backend API for personal finance tracking system"

    # Feature Flags
    ENABLE_EMAIL_SYNC: bool = Field(default=True)
    ENABLE_SCHEDULER: bool = Field(default=True)
    ENABLE_PARSER_AUTO_DISCOVERY: bool = Field(default=True)

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def backup_path(self) -> Path:
        """Get backup directory path."""
        return Path(self.BACKUP_DIR)


# Global settings instance
settings = Settings()
