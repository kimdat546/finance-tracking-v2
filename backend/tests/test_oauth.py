"""Tests for Gmail OAuth2 utilities, services, and the Gmail client wrapper."""

import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import EmailAccount
from app.services.gmail_service import GmailService
from app.services.oauth_service import OAuthService
from app.utils.encryption import EncryptionService, generate_key
from tests.conftest import create_test_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_encryption_service() -> EncryptionService:
    """Return an EncryptionService backed by a freshly generated key."""
    key = Fernet.generate_key().decode("utf-8")
    with patch("app.utils.encryption.settings") as mock_settings:
        mock_settings.ENCRYPTION_KEY = key
        return EncryptionService(key=key)


# ---------------------------------------------------------------------------
# EncryptionService tests
# ---------------------------------------------------------------------------


class TestEncryptionService:
    """Unit tests for :class:`~app.utils.encryption.EncryptionService`."""

    def test_encryption_encrypt_decrypt(self) -> None:
        """Encrypting a value then decrypting it returns the original plaintext."""
        svc = _make_encryption_service()
        original = "my-super-secret-token-12345"
        ciphertext = svc.encrypt(original)
        recovered = svc.decrypt(ciphertext)
        assert recovered == original

    def test_encryption_different_values_produce_different_ciphertexts(self) -> None:
        """Different plaintext inputs produce different ciphertexts."""
        svc = _make_encryption_service()
        ct1 = svc.encrypt("token-abc")
        ct2 = svc.encrypt("token-xyz")
        assert ct1 != ct2

    def test_encryption_same_value_produces_different_ciphertexts(self) -> None:
        """Fernet uses random IV, so the same value encrypted twice differs."""
        svc = _make_encryption_service()
        ct1 = svc.encrypt("same-value")
        ct2 = svc.encrypt("same-value")
        # Ciphertexts should differ (probabilistic encryption)
        assert ct1 != ct2
        # Both should decrypt back to the original
        assert svc.decrypt(ct1) == "same-value"
        assert svc.decrypt(ct2) == "same-value"

    def test_generate_key_format(self) -> None:
        """generate_key() returns a valid base64-encoded Fernet key."""
        key = generate_key()
        # Must be a non-empty string
        assert isinstance(key, str)
        assert len(key) > 0
        # Must be valid base64
        decoded = base64.urlsafe_b64decode(key)
        # Fernet keys are 32 bytes
        assert len(decoded) == 32

    def test_generate_key_is_usable(self) -> None:
        """A key produced by generate_key() can initialise EncryptionService."""
        key = generate_key()
        svc = EncryptionService(key=key)
        ct = svc.encrypt("hello")
        assert svc.decrypt(ct) == "hello"

    def test_encryption_raises_on_empty_key(self) -> None:
        """Constructing EncryptionService with no key raises ValueError."""
        with patch("app.utils.encryption.settings") as mock_settings:
            mock_settings.ENCRYPTION_KEY = ""
            with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
                EncryptionService()

    def test_decrypt_raises_on_tampered_ciphertext(self) -> None:
        """Decrypting a tampered ciphertext raises an error."""
        from cryptography.fernet import InvalidToken

        svc = _make_encryption_service()
        ct = svc.encrypt("some-token")
        tampered = ct[:-4] + "XXXX"
        with pytest.raises(InvalidToken):
            svc.decrypt(tampered)


# ---------------------------------------------------------------------------
# OAuthService tests
# ---------------------------------------------------------------------------


class TestOAuthService:
    """Unit tests for :class:`~app.services.oauth_service.OAuthService`."""

    def _make_service(self, session: AsyncSession) -> OAuthService:
        enc = _make_encryption_service()
        return OAuthService(session=session, encryption=enc)

    @pytest.mark.asyncio
    async def test_oauth_service_get_auth_url(self, test_db: AsyncSession) -> None:
        """get_authorization_url returns a URL containing accounts.google.com."""
        svc = self._make_service(test_db)

        fake_url = "https://accounts.google.com/o/oauth2/auth?client_id=fake&state=abc"
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (fake_url, "abc")

        with (
            patch("app.services.oauth_service.settings") as mock_settings,
            patch("app.services.oauth_service.Flow") as MockFlow,
        ):
            mock_settings.GOOGLE_CLIENT_ID = "fake-client-id"
            mock_settings.GOOGLE_CLIENT_SECRET = "fake-client-secret"
            mock_settings.SECRET_KEY = "test-secret"
            MockFlow.from_client_config.return_value = mock_flow

            url = await svc.get_authorization_url(
                user_id="00000000-0000-0000-0000-000000000001",
                redirect_uri="http://localhost:8000/oauth/callback",
            )

        assert "accounts.google.com" in url

    @pytest.mark.asyncio
    async def test_oauth_service_list_accounts_empty(self, test_db: AsyncSession) -> None:
        """list_accounts returns an empty list for a user with no linked accounts."""
        svc = self._make_service(test_db)
        accounts = await svc.list_accounts("00000000-0000-0000-0000-000000000099")
        assert accounts == []

    @pytest.mark.asyncio
    async def test_oauth_service_list_accounts_returns_accounts(
        self, test_db: AsyncSession
    ) -> None:
        """list_accounts returns accounts belonging to the requested user."""
        svc = self._make_service(test_db)

        await create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000005")
        account = EmailAccount(
            user_id="00000000-0000-0000-0000-000000000005",
            provider="gmail",
            email_address="user@example.com",
        )
        test_db.add(account)
        await test_db.commit()

        accounts = await svc.list_accounts("00000000-0000-0000-0000-000000000005")
        assert len(accounts) == 1
        assert accounts[0].email_address == "user@example.com"

    @pytest.mark.asyncio
    async def test_oauth_service_revoke_returns_false_for_missing_account(
        self, test_db: AsyncSession
    ) -> None:
        """revoke_access returns False when the account does not exist."""
        svc = self._make_service(test_db)
        result = await svc.revoke_access("00000000-0000-0000-0000-ffffffffffff")
        assert result is False

    @pytest.mark.asyncio
    async def test_oauth_service_refresh_returns_false_for_missing_account(
        self, test_db: AsyncSession
    ) -> None:
        """refresh_token returns False when the account does not exist."""
        svc = self._make_service(test_db)
        result = await svc.refresh_token("00000000-0000-0000-0000-ffffffffffff")
        assert result is False


# ---------------------------------------------------------------------------
# EmailAccount model tests
# ---------------------------------------------------------------------------


class TestEmailAccountModel:
    """Integration tests for :class:`~app.models.email.EmailAccount`."""

    @pytest.mark.asyncio
    async def test_email_account_model_creation(self, test_db: AsyncSession) -> None:
        """EmailAccount can be created and persisted to the test database."""
        await create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000006")
        account = EmailAccount(
            user_id="00000000-0000-0000-0000-000000000006",
            provider="gmail",
            email_address="model@example.com",
            is_active=True,
        )
        test_db.add(account)
        await test_db.commit()
        await test_db.refresh(account)

        assert account.id is not None
        assert account.provider == "gmail"
        assert account.email_address == "model@example.com"
        assert account.is_active is True
        assert account.encrypted_access_token is None
        assert account.encrypted_refresh_token is None

    @pytest.mark.asyncio
    async def test_email_account_stores_encrypted_tokens(self, test_db: AsyncSession) -> None:
        """Encrypted token fields are stored and retrieved correctly."""
        await create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000007")
        enc = _make_encryption_service()
        encrypted_access = enc.encrypt("access-token-xyz")
        encrypted_refresh = enc.encrypt("refresh-token-xyz")

        account = EmailAccount(
            user_id="00000000-0000-0000-0000-000000000007",
            provider="gmail",
            email_address="tokentest@example.com",
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expiry=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
        test_db.add(account)
        await test_db.commit()
        await test_db.refresh(account)

        assert account.encrypted_access_token == encrypted_access
        assert account.encrypted_refresh_token == encrypted_refresh
        # Verify tokens survive a round-trip
        assert enc.decrypt(account.encrypted_access_token) == "access-token-xyz"
        assert enc.decrypt(account.encrypted_refresh_token) == "refresh-token-xyz"


# ---------------------------------------------------------------------------
# GmailService tests
# ---------------------------------------------------------------------------


class TestGmailService:
    """Unit tests for :class:`~app.services.gmail_service.GmailService`."""

    def _make_service(self) -> GmailService:
        mock_credentials = MagicMock()
        return GmailService(credentials=mock_credentials)

    def _build_mock_message(
        self,
        html_data: str | None = None,
        text_data: str | None = None,
        multipart: bool = False,
    ) -> dict:
        """Construct a minimal Gmail message dict for testing."""
        if not multipart:
            mime_type = "text/html" if html_data else "text/plain"
            data = html_data or text_data or ""
            encoded = base64.urlsafe_b64encode(data.encode()).decode()
            return {
                "payload": {
                    "mimeType": mime_type,
                    "body": {"data": encoded},
                    "parts": [],
                }
            }

        parts = []
        if text_data:
            parts.append(
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(text_data.encode()).decode()
                    },
                    "parts": [],
                }
            )
        if html_data:
            parts.append(
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode(html_data.encode()).decode()
                    },
                    "parts": [],
                }
            )
        return {
            "payload": {
                "mimeType": "multipart/alternative",
                "body": {},
                "parts": parts,
            }
        }

    @pytest.mark.asyncio
    async def test_gmail_service_get_message_body_html(self) -> None:
        """get_message_body extracts the HTML body from a text/html message."""
        svc = self._make_service()
        html_content = "<p>Hello <b>world</b></p>"
        message = self._build_mock_message(html_data=html_content)

        html_body, text_body = await svc.get_message_body(message)

        assert html_body == html_content
        assert text_body == ""

    @pytest.mark.asyncio
    async def test_gmail_service_get_message_body_text_fallback(self) -> None:
        """get_message_body falls back to plain text when no HTML part is present."""
        svc = self._make_service()
        text_content = "Hello plain world"
        message = self._build_mock_message(text_data=text_content)

        html_body, text_body = await svc.get_message_body(message)

        assert text_body == text_content
        assert html_body == ""

    @pytest.mark.asyncio
    async def test_gmail_service_get_message_body_multipart(self) -> None:
        """get_message_body correctly parses both parts of a multipart message."""
        svc = self._make_service()
        html_content = "<p>Rich content</p>"
        text_content = "Rich content"
        message = self._build_mock_message(
            html_data=html_content,
            text_data=text_content,
            multipart=True,
        )

        html_body, text_body = await svc.get_message_body(message)

        assert html_body == html_content
        assert text_body == text_content

    @pytest.mark.asyncio
    async def test_gmail_service_get_message_body_empty_payload(self) -> None:
        """get_message_body returns empty strings for a message with no body data."""
        svc = self._make_service()
        message: dict = {"payload": {"mimeType": "text/plain", "body": {}, "parts": []}}

        html_body, text_body = await svc.get_message_body(message)

        assert html_body == ""
        assert text_body == ""

    @pytest.mark.asyncio
    async def test_gmail_service_get_profile_calls_api(self) -> None:
        """get_profile invokes the Gmail API and returns the result."""
        svc = self._make_service()
        expected = {"emailAddress": "user@gmail.com", "messagesTotal": 42}

        mock_client = MagicMock()
        mock_client.users.return_value.getProfile.return_value.execute.return_value = expected

        with patch.object(svc, "build_client", return_value=mock_client):
            result = await svc.get_profile()

        assert result == expected

    @pytest.mark.asyncio
    async def test_gmail_service_list_messages_calls_api(self) -> None:
        """list_messages invokes the Gmail API and returns the message list."""
        svc = self._make_service()
        expected = {"messages": [{"id": "msg1", "threadId": "t1"}], "resultSizeEstimate": 1}

        mock_client = MagicMock()
        mock_client.users.return_value.messages.return_value.list.return_value.execute.return_value = (
            expected
        )

        with patch.object(svc, "build_client", return_value=mock_client):
            result = await svc.list_messages(query="from:bank@example.com")

        assert result == expected

    @pytest.mark.asyncio
    async def test_gmail_service_get_message_calls_api(self) -> None:
        """get_message invokes the Gmail API for a specific message ID."""
        svc = self._make_service()
        message_id = "abc123"
        expected = {"id": message_id, "payload": {}}

        mock_client = MagicMock()
        mock_client.users.return_value.messages.return_value.get.return_value.execute.return_value = (
            expected
        )

        with patch.object(svc, "build_client", return_value=mock_client):
            result = await svc.get_message(message_id)

        assert result == expected

    @pytest.mark.asyncio
    async def test_gmail_service_list_history_calls_api(self) -> None:
        """list_history invokes the Gmail API with the provided historyId."""
        svc = self._make_service()
        expected = {"history": [], "historyId": "12345"}

        mock_client = MagicMock()
        mock_client.users.return_value.history.return_value.list.return_value.execute.return_value = (
            expected
        )

        with patch.object(svc, "build_client", return_value=mock_client):
            result = await svc.list_history(start_history_id="11111")

        assert result == expected
