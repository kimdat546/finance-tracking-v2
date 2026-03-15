"""System and configuration database models."""

from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ParserHealthStatus(str, Enum):
    """Parser health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class ParserErrorType(str, Enum):
    """Parser error type enumeration."""

    PARSING_ERROR = "parsing_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


class User(Base):
    """User model - multi-tenant ready."""

    __tablename__ = "users"

    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Database schema (for multi-tenancy)
    schema_name: Mapped[str] = mapped_column(String(100), unique=True)

    # Preferences
    default_currency: Mapped[str] = mapped_column(String(3), default="VND")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="en")

    # Relationships
    user_settings: Mapped[list["UserSetting"]] = relationship(
        "UserSetting", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_user_email", "email"),)


class EmailSyncLog(Base):
    """Log of email synchronization events."""

    __tablename__ = "email_sync_logs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Sync details
    sync_start_time: Mapped[str] = mapped_column(String(50), nullable=False)
    sync_end_time: Mapped[str | None] = mapped_column(String(50))

    # Statistics
    emails_fetched: Mapped[int] = mapped_column(default=0)
    emails_processed: Mapped[int] = mapped_column(default=0)
    emails_with_errors: Mapped[int] = mapped_column(default=0)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("idx_email_sync_user_id", "user_id"),)


class ParserRegistry(Base):
    """Registry of available transaction parsers."""

    __tablename__ = "parser_registry"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Parser identification
    parser_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parser_type: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Parser metadata
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    description: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))

    # Matching rules
    sender_pattern: Mapped[str | None] = mapped_column(String(500))
    subject_pattern: Mapped[str | None] = mapped_column(String(500))
    priority: Mapped[int] = mapped_column(default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_parser_registry_user_id", "user_id"),
        Index("idx_parser_registry_name", "parser_name"),
    )


class ParserVersion(Base):
    """Version history of parsers."""

    __tablename__ = "parser_versions"

    parser_id: Mapped[str] = mapped_column(ForeignKey("parser_registry.id"), nullable=False)

    # Version info
    version_number: Mapped[str] = mapped_column(String(20), nullable=False)
    released_at: Mapped[str] = mapped_column(String(50), nullable=False)

    # Metadata
    changelog: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("idx_parser_version_parser_id", "parser_id"),)


class ParserError(Base):
    """Error logs from parser operations."""

    __tablename__ = "parser_errors"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    parser_id: Mapped[str] = mapped_column(ForeignKey("parser_registry.id"), nullable=False)

    # Error details
    error_type: Mapped[ParserErrorType] = mapped_column(
        Enum(ParserErrorType), nullable=False
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    error_context: Mapped[str | None] = mapped_column(Text)

    # Email info
    email_id: Mapped[str | None] = mapped_column(String(255))
    sender: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(500))

    # Status
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_parser_error_user_id", "user_id"),
        Index("idx_parser_error_parser_id", "parser_id"),
    )


class UnrecognizedEmail(Base):
    """Emails that couldn't be parsed by any parser."""

    __tablename__ = "unrecognized_emails"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Email details
    email_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    received_at: Mapped[str] = mapped_column(String(50), nullable=False)

    # Content
    body_preview: Mapped[str | None] = mapped_column(Text)

    # Processing
    manual_category: Mapped[str | None] = mapped_column(String(255))
    manual_amount: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)

    # Status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_unrecognized_email_user_id", "user_id"),
        Index("idx_unrecognized_email_id", "email_id"),
    )


class ParserHealthAlert(Base):
    """Health alerts for parser systems."""

    __tablename__ = "parser_health_alerts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    parser_id: Mapped[str] = mapped_column(ForeignKey("parser_registry.id"), nullable=False)

    # Alert details
    status: Mapped[ParserHealthStatus] = mapped_column(
        Enum(ParserHealthStatus), default=ParserHealthStatus.HEALTHY
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Metrics
    error_count_24h: Mapped[int] = mapped_column(default=0)
    success_count_24h: Mapped[int] = mapped_column(default=0)
    avg_parse_time_ms: Mapped[float] = mapped_column(default=0.0)

    # Action
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_parser_health_alert_user_id", "user_id"),
        Index("idx_parser_health_alert_parser_id", "parser_id"),
    )


class UserSetting(Base):
    """User-specific settings and preferences."""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Setting key-value
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Type information
    setting_type: Mapped[str] = mapped_column(String(50), default="string")

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="user_settings")

    __table_args__ = (
        Index("idx_user_setting_user_id", "user_id"),
        Index("idx_user_setting_key", "key"),
    )
