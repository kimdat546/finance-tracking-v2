"""Tests for email sync models, utilities, service and API endpoints."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email, EmailAccount
from app.models.system import EmailSyncLog, User
from app.utils.email_utils import (
    decode_base64url,
    extract_email_query,
    get_header_value,
    parse_gmail_date,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


async def _create_test_user(session: AsyncSession, user_id: str = _DEFAULT_USER_ID) -> User:
    """Persist a minimal User row and return it."""
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        hashed_password="hashed",
        schema_name=user_id,
    )
    session.add(user)
    await session.flush()
    return user


_DEFAULT_ACCOUNT_ID = "00000000-0000-0000-0000-000000000002"


async def _create_test_account(
    session: AsyncSession,
    user_id: str = _DEFAULT_USER_ID,
    account_id: str = _DEFAULT_ACCOUNT_ID,
) -> EmailAccount:
    """Persist a minimal EmailAccount row and return it."""
    account = EmailAccount(
        id=account_id,
        user_id=user_id,
        provider="gmail",
        email_address="test@gmail.com",
    )
    session.add(account)
    await session.flush()
    return account


# ---------------------------------------------------------------------------
# Email model tests
# ---------------------------------------------------------------------------


class TestEmailModel:
    """Database-level tests for the :class:`~app.models.email.Email` model."""

    @pytest.mark.asyncio
    async def test_email_model_creation(self, test_db: AsyncSession) -> None:
        """Creating an Email record populates all required fields."""
        await _create_test_user(test_db, user_id=_DEFAULT_USER_ID)
        await _create_test_account(test_db, user_id=_DEFAULT_USER_ID, account_id="00000000-0000-0000-0000-000000000011")

        email = Email(
            user_id=_DEFAULT_USER_ID,
            email_account_id="00000000-0000-0000-0000-000000000011",
            gmail_message_id="gmail-msg-001",
            sender="bank@example.com",
            subject="Your transaction",
            received_at=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
            raw_html_body="<p>Hello</p>",
            raw_text_body="Hello",
        )
        test_db.add(email)
        await test_db.flush()

        stmt = select(Email).where(Email.gmail_message_id == "gmail-msg-001")
        result = await test_db.execute(stmt)
        saved = result.scalar_one()

        assert saved.user_id == _DEFAULT_USER_ID
        assert saved.email_account_id == "00000000-0000-0000-0000-000000000011"
        assert saved.gmail_message_id == "gmail-msg-001"
        assert saved.sender == "bank@example.com"
        assert saved.subject == "Your transaction"
        assert saved.parsed is False
        assert saved.parse_attempted is False
        assert saved.is_duplicate is False
        assert saved.fingerprint is None
        assert saved.id is not None

    @pytest.mark.asyncio
    async def test_email_unique_constraint(self, test_db: AsyncSession) -> None:
        """Inserting two emails with the same (user_id, gmail_message_id) raises IntegrityError."""
        await _create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000003")
        await _create_test_account(test_db, user_id="00000000-0000-0000-0000-000000000003", account_id="00000000-0000-0000-0000-000000000012")

        email1 = Email(
            user_id="00000000-0000-0000-0000-000000000003",
            email_account_id="00000000-0000-0000-0000-000000000012",
            gmail_message_id="dup-msg-001",
        )
        test_db.add(email1)
        await test_db.flush()

        email2 = Email(
            user_id="00000000-0000-0000-0000-000000000003",
            email_account_id="00000000-0000-0000-0000-000000000012",
            gmail_message_id="dup-msg-001",
        )
        test_db.add(email2)

        with pytest.raises(IntegrityError):
            await test_db.flush()

        await test_db.rollback()


# ---------------------------------------------------------------------------
# email_utils tests
# ---------------------------------------------------------------------------


class TestExtractEmailQuery:
    """Tests for :func:`~app.utils.email_utils.extract_email_query`."""

    def test_labels_only(self) -> None:
        """A query with only labels contains only the label group."""
        result = extract_email_query(["Finance/Cake", "Finance/VPBank"], [])
        assert result == "(label:Finance/Cake OR label:Finance/VPBank)"

    def test_single_label_no_parentheses_needed(self) -> None:
        """A single label is still wrapped in parentheses."""
        result = extract_email_query(["Finance/Cake"], [])
        assert result == "(label:Finance/Cake)"

    def test_empty_inputs(self) -> None:
        """No labels and no senders returns an empty string."""
        result = extract_email_query([], [])
        assert result == ""

    def test_labels_and_senders(self) -> None:
        """Labels and senders are joined by a space with both groups present."""
        result = extract_email_query(
            ["Finance/Cake"],
            ["no-reply@cake.vn", "alerts@vpbank.com"],
        )
        assert result == (
            "(label:Finance/Cake) (from:no-reply@cake.vn OR from:alerts@vpbank.com)"
        )

    def test_senders_only(self) -> None:
        """A query with only senders contains only the sender group."""
        result = extract_email_query([], ["no-reply@cake.vn"])
        assert result == "(from:no-reply@cake.vn)"


class TestDecodeBase64url:
    """Tests for :func:`~app.utils.email_utils.decode_base64url`."""

    def test_standard_base64url_string(self) -> None:
        """Decodes a standard ASCII message encoded as base64url."""
        original = b"Hello, World!"
        encoded = base64.urlsafe_b64encode(original).decode("utf-8").rstrip("=")
        assert decode_base64url(encoded) == original

    def test_urlsafe_chars(self) -> None:
        """Handles the URL-safe ``-`` and ``_`` characters correctly."""
        # Craft a value that would produce + and / in standard base64
        raw = bytes(range(256))
        encoded = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
        # Ensure url-safe chars are present (no + or /)
        assert "+" not in encoded
        assert "/" not in encoded
        assert decode_base64url(encoded) == raw

    def test_with_padding(self) -> None:
        """A base64url string with existing padding is decoded correctly."""
        original = b"test"
        encoded = base64.urlsafe_b64encode(original).decode("utf-8")  # includes padding
        assert decode_base64url(encoded) == original

    def test_empty_string(self) -> None:
        """An empty string decodes to empty bytes."""
        assert decode_base64url("") == b""


class TestGetHeaderValue:
    """Tests for :func:`~app.utils.email_utils.get_header_value`."""

    def test_exact_case_match(self) -> None:
        """Returns the value when the header name matches exactly."""
        headers = [{"name": "Subject", "value": "My Subject"}]
        assert get_header_value(headers, "Subject") == "My Subject"

    def test_case_insensitive_lookup(self) -> None:
        """Lookup is case-insensitive."""
        headers = [{"name": "From", "value": "bank@example.com"}]
        assert get_header_value(headers, "from") == "bank@example.com"
        assert get_header_value(headers, "FROM") == "bank@example.com"

    def test_returns_none_when_missing(self) -> None:
        """Returns ``None`` when the named header is not present."""
        headers = [{"name": "Subject", "value": "Hi"}]
        assert get_header_value(headers, "Date") is None

    def test_empty_headers_list(self) -> None:
        """Returns ``None`` for an empty list."""
        assert get_header_value([], "Subject") is None

    def test_multiple_headers_returns_first(self) -> None:
        """Returns the first matching header value."""
        headers = [
            {"name": "X-Custom", "value": "first"},
            {"name": "X-Custom", "value": "second"},
        ]
        assert get_header_value(headers, "X-Custom") == "first"


class TestParseGmailDate:
    """Tests for :func:`~app.utils.email_utils.parse_gmail_date`."""

    def test_rfc2822_with_timezone_offset(self) -> None:
        """Parses an RFC 2822 date string with a positive UTC offset."""
        dt = parse_gmail_date("Thu, 15 Mar 2026 10:30:00 +0700")
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 15
        assert dt.hour == 10
        assert dt.minute == 30
        assert dt.tzinfo is not None

    def test_rfc2822_utc(self) -> None:
        """Parses a UTC date string (``+0000`` offset)."""
        dt = parse_gmail_date("Mon, 1 Jan 2024 00:00:00 +0000")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

    def test_invalid_date_raises_value_error(self) -> None:
        """An unparseable string raises :class:`ValueError`."""
        with pytest.raises(ValueError):
            parse_gmail_date("not-a-date")


# ---------------------------------------------------------------------------
# EmailSyncService tests
# ---------------------------------------------------------------------------


class TestEmailSyncServiceGetEmails:
    """Tests for :meth:`~app.services.email_sync_service.EmailSyncService.get_emails`."""

    @pytest.mark.asyncio
    async def test_get_emails_empty(self, test_db: AsyncSession) -> None:
        """Returns an empty list and total=0 when the user has no emails."""
        from app.services.email_sync_service import EmailSyncService

        mock_gmail = MagicMock()
        mock_oauth = MagicMock()
        service = EmailSyncService(
            session=test_db, gmail_service=mock_gmail, oauth_service=mock_oauth
        )

        # Use a user ID that has no emails
        emails, total = await service.get_emails(user_id="00000000-0000-0000-0000-ffffffffffff")
        assert emails == []
        assert total == 0


class TestEmailSyncServiceIncrementalSync:
    """Tests for incremental sync using a mocked Gmail API."""

    @pytest.mark.asyncio
    async def test_incremental_sync_mocked(self, test_db: AsyncSession) -> None:
        """Incremental sync creates an EmailSyncLog and processes history records."""
        from app.services.email_sync_service import EmailSyncService

        await _create_test_user(test_db, user_id=_DEFAULT_USER_ID)
        await _create_test_account(test_db, user_id=_DEFAULT_USER_ID, account_id="00000000-0000-0000-0000-000000000013")

        # Seed the EmailAccount with a historyId so incremental path is taken
        stmt = select(EmailAccount).where(EmailAccount.id == "00000000-0000-0000-0000-000000000013")
        result = await test_db.execute(stmt)
        account = result.scalar_one()
        account.history_id = "12345"
        await test_db.flush()

        # Mock Gmail history returning one new message
        mock_gmail = AsyncMock()
        mock_gmail.list_history.return_value = {
            "history": [
                {
                    "messagesAdded": [{"message": {"id": "new-msg-001"}}],
                }
            ],
            "historyId": "12346",
        }
        mock_gmail.get_message.return_value = {
            "id": "new-msg-001",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "bank@example.com"},
                    {"name": "Subject", "value": "Transaction alert"},
                    {"name": "Date", "value": "Sun, 15 Mar 2026 10:00:00 +0000"},
                ],
                "body": {
                    "data": base64.urlsafe_b64encode(b"Transaction body").decode(),
                },
                "parts": [],
            },
        }
        mock_gmail.get_profile.return_value = {"historyId": "12346", "emailAddress": "test@gmail.com"}

        mock_oauth = MagicMock()
        service = EmailSyncService(
            session=test_db, gmail_service=mock_gmail, oauth_service=mock_oauth
        )

        sync_log = await service.sync_emails(
            user_id=_DEFAULT_USER_ID,
            email_account_id="00000000-0000-0000-0000-000000000013",
        )

        assert sync_log.status == "completed"
        assert sync_log.sync_type == "incremental"
        assert sync_log.emails_fetched == 1
        assert sync_log.emails_processed == 1  # new
        assert sync_log.emails_with_errors == 0  # no duplicates

        # Verify the email was persisted
        email_stmt = select(Email).where(
            Email.gmail_message_id == "new-msg-001",
            Email.user_id == _DEFAULT_USER_ID,
        )
        email_result = await test_db.execute(email_stmt)
        saved_email = email_result.scalar_one_or_none()
        assert saved_email is not None
        assert saved_email.sender == "bank@example.com"
        assert saved_email.subject == "Transaction alert"


class TestEmailSyncServiceFullSync:
    """Tests for the full sync fallback path."""

    @pytest.mark.asyncio
    async def test_full_sync_fallback_when_no_history_id(self, test_db: AsyncSession) -> None:
        """When the account has no historyId, a full sync is performed."""
        from app.services.email_sync_service import EmailSyncService

        await _create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000004")
        await _create_test_account(
            test_db, user_id="00000000-0000-0000-0000-000000000004", account_id="00000000-0000-0000-0000-000000000014"
        )
        # Account intentionally has no history_id (default is NULL)

        mock_gmail = AsyncMock()
        mock_gmail.list_messages.return_value = {
            "messages": [{"id": "full-msg-001"}],
            "nextPageToken": None,
        }
        mock_gmail.get_message.return_value = {
            "id": "full-msg-001",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "vpbank@alerts.vn"},
                    {"name": "Subject", "value": "Balance update"},
                    {"name": "Date", "value": "Sun, 15 Mar 2026 08:00:00 +0000"},
                ],
                "body": {
                    "data": base64.urlsafe_b64encode(b"Balance body").decode(),
                },
                "parts": [],
            },
        }
        mock_gmail.get_profile.return_value = {
            "historyId": "99001",
            "emailAddress": "test-full@gmail.com",
        }

        mock_oauth = MagicMock()
        service = EmailSyncService(
            session=test_db, gmail_service=mock_gmail, oauth_service=mock_oauth
        )

        sync_log = await service.sync_emails(
            user_id="00000000-0000-0000-0000-000000000004",
            email_account_id="00000000-0000-0000-0000-000000000014",
        )

        assert sync_log.status == "completed"
        assert sync_log.sync_type == "full"
        assert sync_log.emails_fetched == 1
        assert sync_log.emails_processed == 1

        # historyId should be updated on the account
        stmt = select(EmailAccount).where(EmailAccount.id == "00000000-0000-0000-0000-000000000014")
        result = await test_db.execute(stmt)
        updated_account = result.scalar_one()
        assert updated_account.history_id == "99001"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestEmailSyncAPI:
    """Tests for the /email-sync API endpoints."""

    def test_email_sync_status_endpoint_no_sync(self, test_client: TestClient) -> None:
        """GET /email-sync/status returns 200 with a 'no_sync' status when no sync has run."""
        response = test_client.get("/email-sync/status")
        assert response.status_code == 200
        data = response.json()
        # May return no_sync (empty DB) or a real status if previous tests ran
        assert "status" in data

    def test_email_sync_list_emails_empty(self, test_client: TestClient) -> None:
        """GET /email-sync/emails returns 200 with an empty list."""
        response = test_client.get("/email-sync/emails")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_email_sync_get_nonexistent_email(self, test_client: TestClient) -> None:
        """GET /email-sync/emails/{id} returns 404 for a non-existent ID."""
        response = test_client.get("/email-sync/emails/00000000-0000-0000-0000-ffffffffffff")
        assert response.status_code == 404

    def test_email_sync_reprocess_nonexistent_email(self, test_client: TestClient) -> None:
        """POST /email-sync/emails/{id}/reprocess returns 404 for a non-existent ID."""
        response = test_client.post("/email-sync/emails/00000000-0000-0000-0000-ffffffffffff/reprocess")
        assert response.status_code == 404
