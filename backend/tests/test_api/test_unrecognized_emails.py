"""Tests for the unrecognized-email queue service and API endpoints."""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import User
from app.services.unrecognized_email_service import UnrecognizedEmailService
from tests.conftest import create_test_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest_asyncio.fixture
async def unrecognized_user(test_db: AsyncSession) -> User:
    """Create the test user required by UnrecognizedEmail FK constraints."""
    return await create_test_user(test_db, user_id=USER_ID)


async def _make_record(
    service: UnrecognizedEmailService,
    *,
    email_id: str = "email-001",
    sender: str = "bank@example.com",
    subject: str = "Your transaction",
    received_at: str = "2026-03-01T10:00:00",
    raw_body: str | None = "Amount: 100.00 Date: 01/03/2026 Ref: TXN123456",
    parse_error: str | None = "No parser matched",
    parsed_attempt: dict | None = None,
):
    """Convenience wrapper around ``record_unrecognized``."""
    return await service.record_unrecognized(
        user_id=USER_ID,
        email_id=email_id,
        sender=sender,
        subject=subject,
        received_at=received_at,
        raw_body=raw_body,
        parse_error=parse_error,
        parsed_attempt=parsed_attempt,
    )


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_unrecognized_email(test_db: AsyncSession, unrecognized_user: User) -> None:
    """Creating a new record persists it and returns the ORM object."""
    service = UnrecognizedEmailService(test_db)
    record = await _make_record(service)

    assert record.id is not None
    assert record.email_id == "email-001"
    assert record.sender == "bank@example.com"
    assert record.status == "pending"
    assert record.raw_body is not None
    assert "Amount" in record.raw_body


@pytest.mark.asyncio
async def test_record_same_email_updates(test_db: AsyncSession, unrecognized_user: User) -> None:
    """Recording the same email_id twice updates rather than duplicating."""
    service = UnrecognizedEmailService(test_db)

    first = await _make_record(service, email_id="dup-001", subject="Original subject")
    second = await _make_record(service, email_id="dup-001", subject="Updated subject")

    assert first.id == second.id, "Same PK expected on upsert"
    assert second.subject == "Updated subject"


@pytest.mark.asyncio
async def test_list_unrecognized_empty(test_db: AsyncSession) -> None:
    """A new user has no unrecognized emails."""
    service = UnrecognizedEmailService(test_db)
    items, total = await service.list_unrecognized(user_id="00000000-0000-0000-0000-000000000099")
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_unrecognized_with_filter(test_db: AsyncSession, unrecognized_user: User) -> None:
    """Filtering by status returns only matching records."""
    service = UnrecognizedEmailService(test_db)
    r1 = await _make_record(service, email_id="filter-001")
    await service.mark_as_ignored(r1.id, USER_ID)

    await _make_record(service, email_id="filter-002")

    pending_items, pending_total = await service.list_unrecognized(
        user_id=USER_ID, status="pending"
    )
    ignored_items, ignored_total = await service.list_unrecognized(
        user_id=USER_ID, status="ignored"
    )

    assert pending_total >= 1
    assert ignored_total >= 1
    assert all(i.status == "pending" for i in pending_items)
    assert all(i.status == "ignored" for i in ignored_items)


@pytest.mark.asyncio
async def test_mark_as_ignored(test_db: AsyncSession, unrecognized_user: User) -> None:
    """mark_as_ignored sets status to 'ignored' and is_processed to True."""
    service = UnrecognizedEmailService(test_db)
    record = await _make_record(service, email_id="ignore-001")

    updated = await service.mark_as_ignored(record.id, USER_ID)

    assert updated is not None
    assert updated.status == "ignored"
    assert updated.is_processed is True


@pytest.mark.asyncio
async def test_categorize_email(test_db: AsyncSession, unrecognized_user: User) -> None:
    """mark_as_categorized sets status, manual_category and optional fields."""
    service = UnrecognizedEmailService(test_db)
    record = await _make_record(service, email_id="cat-001")

    updated = await service.mark_as_categorized(
        email_id=record.id,
        user_id=USER_ID,
        category="Groceries",
        amount="99.90",
        notes="Supermarket receipt",
    )

    assert updated is not None
    assert updated.status == "categorized"
    assert updated.manual_category == "Groceries"
    assert updated.manual_amount == "99.90"
    assert updated.notes == "Supermarket receipt"
    assert updated.is_processed is True


@pytest.mark.asyncio
async def test_bulk_update_status(test_db: AsyncSession, unrecognized_user: User) -> None:
    """bulk_update_status updates all supplied IDs and returns the count."""
    service = UnrecognizedEmailService(test_db)
    r1 = await _make_record(service, email_id="bulk-001")
    r2 = await _make_record(service, email_id="bulk-002")

    count = await service.bulk_update_status(
        user_id=USER_ID,
        email_ids=[r1.id, r2.id],
        status="ignored",
    )
    assert count == 2

    # Verify persisted state
    updated_r1 = await service.get_by_id(r1.id, USER_ID)
    updated_r2 = await service.get_by_id(r2.id, USER_ID)
    assert updated_r1 is not None and updated_r1.status == "ignored"
    assert updated_r2 is not None and updated_r2.status == "ignored"


@pytest.mark.asyncio
async def test_delete_emails(test_db: AsyncSession, unrecognized_user: User) -> None:
    """delete_by_ids removes records and returns the deleted count."""
    service = UnrecognizedEmailService(test_db)
    r1 = await _make_record(service, email_id="del-001")
    r2 = await _make_record(service, email_id="del-002")

    count = await service.delete_by_ids(user_id=USER_ID, email_ids=[r1.id, r2.id])
    assert count == 2

    assert await service.get_by_id(r1.id, USER_ID) is None
    assert await service.get_by_id(r2.id, USER_ID) is None


@pytest.mark.asyncio
async def test_analytics_structure(test_db: AsyncSession, unrecognized_user: User) -> None:
    """get_analytics returns all expected top-level keys."""
    service = UnrecognizedEmailService(test_db)
    await _make_record(service, email_id="analytics-001")

    analytics = await service.get_analytics(user_id=USER_ID)

    assert "total" in analytics
    assert "by_status" in analytics
    assert "by_sender" in analytics
    assert "rate_last_7_days" in analytics
    assert isinstance(analytics["total"], int)
    assert isinstance(analytics["by_status"], dict)
    assert isinstance(analytics["by_sender"], list)
    assert isinstance(analytics["rate_last_7_days"], float)
    # by_status must have at least the four canonical keys
    for key in ("pending", "ignored", "categorized", "rule_created"):
        assert key in analytics["by_status"]


@pytest.mark.asyncio
async def test_export_json(test_db: AsyncSession, unrecognized_user: User) -> None:
    """export_emails with format='json' returns valid JSON containing the record."""
    service = UnrecognizedEmailService(test_db)
    await _make_record(service, email_id="export-001")

    exported = await service.export_emails(user_id=USER_ID, format="json")
    data = json.loads(exported)

    assert isinstance(data, list)
    assert len(data) >= 1
    assert "email_id" in data[0]


@pytest.mark.asyncio
async def test_suggest_rules_has_suggestions(test_db: AsyncSession, unrecognized_user: User) -> None:
    """suggest_parser_rules returns a non-empty list for an email with body text."""
    service = UnrecognizedEmailService(test_db)
    record = await _make_record(
        service,
        email_id="suggest-001",
        raw_body="Amount: 1,234.56 Date: 01/03/2026 Ref: TXN987654",
    )

    suggestions = await service.suggest_parser_rules(record.id, USER_ID)

    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    # Each suggestion must have required keys
    for suggestion in suggestions:
        assert "field" in suggestion
        assert "pattern" in suggestion
        assert "confidence" in suggestion
        assert 0.0 <= suggestion["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


def test_api_list_endpoint(test_client) -> None:
    """GET /unrecognized-emails returns HTTP 200 with a valid list response."""
    response = test_client.get("/unrecognized-emails")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
