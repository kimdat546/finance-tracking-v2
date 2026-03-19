"""Schemas for unrecognized email endpoints."""

import json
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UnrecognizedEmailSchema(BaseModel):
    """Public view of an unrecognized email record."""

    id: str = Field(description="Record ID")
    email_id: str = Field(description="Original email ID")
    sender: str = Field(description="Sender email address")
    subject: str = Field(description="Email subject")
    received_at: str = Field(description="Date/time the email was received")
    status: str = Field(description="Processing status")
    parse_error: str | None = Field(default=None, description="Reason parse failed")
    manual_category: str | None = Field(default=None, description="Manually assigned category")
    created_at: datetime = Field(description="Record creation timestamp")

    model_config = {"from_attributes": True}


class UnrecognizedEmailDetailSchema(UnrecognizedEmailSchema):
    """Detailed view of an unrecognized email, including raw content."""

    raw_body: str | None = Field(default=None, description="First 1000 chars of raw email body")
    parsed_attempt: dict | None = Field(
        default=None, description="Partially extracted fields from the email"
    )
    similar_transaction_ids: list[str] = Field(
        default_factory=list, description="IDs of similar transactions"
    )

    @classmethod
    def from_orm_with_truncation(cls, obj: object) -> "UnrecognizedEmailDetailSchema":
        """Build schema from ORM object, truncating raw_body to 1000 chars."""
        raw_body = getattr(obj, "raw_body", None)
        if raw_body:
            raw_body = raw_body[:1000]

        parsed_attempt_raw = getattr(obj, "parsed_attempt", None)
        parsed_attempt: dict | None = None
        if parsed_attempt_raw:
            try:
                parsed_attempt = json.loads(parsed_attempt_raw)
            except (json.JSONDecodeError, TypeError):
                parsed_attempt = None

        similar_raw = getattr(obj, "similar_transaction_ids", None)
        similar_ids: list[str] = []
        if similar_raw:
            try:
                similar_ids = json.loads(similar_raw)
            except (json.JSONDecodeError, TypeError):
                similar_ids = []

        return cls(
            id=obj.id,
            email_id=obj.email_id,
            sender=obj.sender,
            subject=obj.subject,
            received_at=obj.received_at,
            status=obj.status,
            parse_error=obj.parse_error,
            manual_category=obj.manual_category,
            created_at=obj.created_at,
            raw_body=raw_body,
            parsed_attempt=parsed_attempt,
            similar_transaction_ids=similar_ids,
        )


class CategorizeRequest(BaseModel):
    """Request body for manually categorizing an unrecognized email."""

    category: str = Field(description="Category name to assign")
    amount: str | None = Field(default=None, description="Manually entered transaction amount")
    notes: str | None = Field(default=None, description="Optional notes")


class BulkUpdateRequest(BaseModel):
    """Request body for bulk-updating email statuses."""

    email_ids: list[str] = Field(description="List of unrecognized-email record IDs to update")
    status: str = Field(description="New status to set")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Ensure status is a valid value."""
        allowed = {"pending", "ignored", "categorized"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class BulkDeleteRequest(BaseModel):
    """Request body for bulk-deleting unrecognized email records."""

    email_ids: list[str] = Field(description="List of unrecognized-email record IDs to delete")


class UnrecognizedListResponse(BaseModel):
    """Paginated list response for unrecognized emails."""

    items: list[UnrecognizedEmailSchema] = Field(description="Page of unrecognized email records")
    total: int = Field(description="Total number of matching records")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")


class AnalyticsResponse(BaseModel):
    """Analytics summary for unrecognized emails."""

    total: int = Field(description="Total unrecognized email records")
    by_status: dict = Field(description="Count per status value")
    by_sender: list[dict] = Field(description="Top senders by unrecognized email count")
    rate_last_7_days: float = Field(description="Approximate unrecognized rate over last 7 days")


class RuleSuggestion(BaseModel):
    """A single suggested parser rule."""

    field: str = Field(description="The email field this rule targets")
    pattern: str = Field(description="Regex pattern to match the field value")
    confidence: float = Field(description="Confidence score between 0 and 1")


class RuleSuggestionsResponse(BaseModel):
    """Response containing suggested parser rules for an unrecognized email."""

    email_id: str = Field(description="ID of the unrecognized email record")
    suggestions: list[RuleSuggestion] = Field(description="List of rule suggestions")


class ExportRequest(BaseModel):
    """Request body for exporting unrecognized emails."""

    format: str = Field(default="json", description="Export format: 'json' or 'csv'")
    status: str | None = Field(default=None, description="Filter by status before export")
