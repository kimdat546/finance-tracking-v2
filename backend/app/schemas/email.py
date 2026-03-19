"""Pydantic v2 schemas for email sync API endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EmailSyncRequest(BaseModel):
    """Request body for triggering an email synchronisation run.

    Attributes:
        trigger_full_sync: When ``True`` the service ignores any stored
            ``historyId`` and performs a full label/sender search.
        labels: Gmail label names to filter by.  Falls back to the service
            default (``["Finance/Cake", "Finance/VPBank"]``) when empty.
        senders: Sender e-mail addresses to filter by.  No sender filter is
            applied when empty.
    """

    trigger_full_sync: bool = Field(
        default=False,
        description="Force a full sync, ignoring any stored Gmail historyId.",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Gmail label names to include in the search query.",
    )
    senders: list[str] = Field(
        default_factory=list,
        description="Sender e-mail addresses to filter by.",
    )


class EmailSyncResponse(BaseModel):
    """Response body returned after an email synchronisation run.

    Attributes:
        sync_log_id: Primary key of the created :class:`~app.models.system.EmailSyncLog`.
        emails_fetched: Total number of message IDs retrieved from Gmail.
        emails_new: Number of messages persisted for the first time.
        emails_duplicate: Number of messages that already existed in the DB.
        status: Final status of the sync (``"completed"`` or ``"failed"``).
        message: Human-readable summary of the sync outcome.
    """

    sync_log_id: str = Field(description="ID of the EmailSyncLog record created for this run.")
    emails_fetched: int = Field(description="Total emails fetched from Gmail.")
    emails_new: int = Field(description="New emails persisted to the database.")
    emails_duplicate: int = Field(description="Emails already present in the database.")
    status: str = Field(description="Sync status: 'completed' or 'failed'.")
    message: str = Field(description="Human-readable outcome description.")


class EmailSchema(BaseModel):
    """Public view of a stored email message.

    Attributes:
        id: Database primary key (UUID string).
        gmail_message_id: The Gmail message ID.
        sender: Sender address extracted from the ``From`` header.
        subject: Email subject line.
        received_at: Timezone-aware timestamp the message was received.
        parsed: Whether a bank parser successfully processed this email.
        is_duplicate: Whether this email was identified as a duplicate.
    """

    model_config = {"from_attributes": True}

    id: str = Field(description="Database primary key.")
    gmail_message_id: str = Field(description="Gmail message ID.")
    sender: str | None = Field(default=None, description="Sender email address.")
    subject: str | None = Field(default=None, description="Email subject line.")
    received_at: datetime | None = Field(
        default=None, description="Timezone-aware receipt timestamp."
    )
    parsed: bool = Field(description="True if a parser successfully processed this email.")
    is_duplicate: bool = Field(description="True if identified as a duplicate.")


class EmailListResponse(BaseModel):
    """Paginated list of email messages.

    Attributes:
        items: Page of :class:`EmailSchema` objects.
        total: Total number of emails matching the query.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    items: list[EmailSchema] = Field(description="Emails on the current page.")
    total: int = Field(description="Total matching email count.")
    page: int = Field(description="Current page number (1-indexed).")
    page_size: int = Field(description="Number of items per page.")
