"""Email account and email models for Gmail sync."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailAccount(Base):
    """Stores Gmail OAuth credentials and sync state for a user's linked email account.

    Each row represents a single Gmail account linked to a user.
    Tokens are stored encrypted via :class:`~app.utils.encryption.EncryptionService`.
    """

    __tablename__ = "email_accounts"

    # Ownership
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider info
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gmail")
    email_address: Mapped[str] = mapped_column(String(255), nullable=False)

    # Encrypted OAuth tokens (Text for SQLite compatibility)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Token metadata
    token_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Account state
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Sync tracking
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    history_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Gmail historyId for incremental sync

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "email_address", name="uq_email_account"),
        Index("idx_email_account_user_id", "user_id"),
        Index("idx_email_account_email_address", "email_address"),
        Index("idx_email_account_is_active", "is_active"),
    )


class Email(Base):
    """Stores individual Gmail messages fetched during sync.

    Each row represents a single email message associated with a user and an email account.
    Raw HTML and plain-text bodies are stored for subsequent parsing by bank parsers.
    """

    __tablename__ = "emails"

    # Ownership
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email_account_id: Mapped[str] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Gmail identifier
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Message metadata
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Full message bodies
    raw_html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Processing flags
    parsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parse_attempted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sync_log_id: Mapped[str | None] = mapped_column(
        ForeignKey("email_sync_logs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Deduplication fingerprint (populated in WBS-001-04)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("user_id", "gmail_message_id", name="uq_email_user_gmail_message"),
        Index("idx_email_user_parsed", "user_id", "parsed"),
        Index("idx_email_user_received_at", "user_id", "received_at"),
        Index(
            "idx_email_fingerprint_user",
            "fingerprint",
            "user_id",
        ),
    )
