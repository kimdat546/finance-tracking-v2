"""OAuth2 token management service for Gmail integration."""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.email import EmailAccount
from app.utils.encryption import EncryptionService

logger = logging.getLogger(__name__)

GMAIL_SCOPES: list[str] = ["https://www.googleapis.com/auth/gmail.readonly"]

# Access tokens expiring within this many seconds are proactively refreshed.
_REFRESH_THRESHOLD_SECONDS: int = 300  # 5 minutes


class OAuthService:
    """Manages Gmail OAuth2 authorization flows and token lifecycle.

    Responsibilities:
    - Build the Google authorization URL with a signed CSRF state token.
    - Exchange an authorization code for access/refresh tokens.
    - Persist encrypted tokens to the database via :class:`~app.models.email.EmailAccount`.
    - Refresh access tokens automatically when they are about to expire.
    - Revoke access and clean up stored tokens.
    """

    def __init__(self, session: AsyncSession, encryption: EncryptionService) -> None:
        """Initialize the OAuthService.

        Args:
            session: An async SQLAlchemy session for database operations.
            encryption: An :class:`~app.utils.encryption.EncryptionService` instance for
                encrypting and decrypting tokens.
        """
        self._session = session
        self._encryption = encryption

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_flow(self, redirect_uri: str) -> Flow:
        """Build a google-auth-oauthlib Flow from application settings.

        Args:
            redirect_uri: The redirect URI to include in the OAuth2 request.

        Returns:
            A configured :class:`~google_auth_oauthlib.flow.Flow` instance.
        """
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri=redirect_uri,
        )
        return flow

    def _generate_state(self, user_id: str) -> str:
        """Generate an HMAC-signed state token for CSRF protection.

        Args:
            user_id: The user ID to embed in the state token.

        Returns:
            A hex string state token in the form ``<nonce>.<hmac>``.
        """
        nonce = secrets.token_hex(16)
        payload = f"{user_id}:{nonce}"
        signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{payload}.{signature}"

    def _verify_state(self, state: str, user_id: str) -> bool:
        """Verify that the state token was produced by :meth:`_generate_state`.

        Args:
            state: The state token received from the OAuth2 callback.
            user_id: The user ID to validate against.

        Returns:
            True if the state is valid; False otherwise.
        """
        try:
            parts = state.rsplit(".", 1)
            if len(parts) != 2:
                return False
            payload, received_sig = parts
            expected_sig = hmac.new(
                settings.SECRET_KEY.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected_sig, received_sig):
                return False
            embedded_user_id = payload.split(":")[0]
            return embedded_user_id == user_id
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_authorization_url(self, user_id: str, redirect_uri: str) -> str:
        """Build a Google OAuth2 authorization URL for the given user.

        Args:
            user_id: The ID of the user initiating the flow.
            redirect_uri: The URI Google should redirect to after authorization.

        Returns:
            The full authorization URL to redirect the user's browser to.
        """
        flow = self._build_flow(redirect_uri)
        state = self._generate_state(user_id)
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        logger.info("Generated authorization URL for user %s (token: ***)", user_id)
        return authorization_url

    async def handle_callback(
        self,
        user_id: str,
        code: str,
        state: str,
        redirect_uri: str,
    ) -> EmailAccount:
        """Exchange an authorization code for tokens and persist them.

        Args:
            user_id: The ID of the user completing the OAuth2 flow.
            code: The authorization code returned by Google.
            state: The CSRF state token to verify.
            redirect_uri: Must match the URI used during authorization.

        Returns:
            The created or updated :class:`~app.models.email.EmailAccount`.

        Raises:
            ValueError: If the state token is invalid.
            Exception: Re-raised on Google token exchange failures.
        """
        if not self._verify_state(state, user_id):
            logger.warning("OAuth2 state verification failed for user %s", user_id)
            raise ValueError("Invalid OAuth2 state token. Possible CSRF attack.")

        flow = self._build_flow(redirect_uri)
        flow.fetch_token(code=code)
        credentials: Credentials = flow.credentials

        # Retrieve Gmail address via the userinfo endpoint
        import googleapiclient.discovery as discovery  # noqa: PLC0415

        oauth2_service = discovery.build("oauth2", "v2", credentials=credentials)
        user_info: dict = oauth2_service.userinfo().get().execute()
        email_address: str = user_info.get("email", "")

        if not email_address:
            raise ValueError("Could not determine email address from Google credentials.")

        # Upsert EmailAccount
        stmt = select(EmailAccount).where(
            EmailAccount.user_id == user_id,
            EmailAccount.provider == "gmail",
            EmailAccount.email_address == email_address,
        )
        result = await self._session.execute(stmt)
        account: EmailAccount | None = result.scalar_one_or_none()

        if account is None:
            account = EmailAccount(
                user_id=user_id,
                provider="gmail",
                email_address=email_address,
            )
            self._session.add(account)

        # Store encrypted tokens
        if credentials.token:
            account.encrypted_access_token = self._encryption.encrypt(credentials.token)
        if credentials.refresh_token:
            account.encrypted_refresh_token = self._encryption.encrypt(credentials.refresh_token)
        if credentials.expiry:
            account.token_expiry = credentials.expiry.replace(tzinfo=timezone.utc)
        account.is_active = True

        await self._session.commit()
        await self._session.refresh(account)

        logger.info(
            "OAuth2 callback handled for user %s, email %s (tokens: ***)",
            user_id,
            email_address,
        )
        return account

    async def refresh_token(self, email_account_id: str) -> bool:
        """Refresh the access token for the given email account.

        Args:
            email_account_id: The primary key of the :class:`~app.models.email.EmailAccount`.

        Returns:
            True if the token was refreshed successfully; False otherwise.
        """
        account = await self._get_account_by_id(email_account_id)
        if account is None:
            logger.warning("refresh_token: account %s not found", email_account_id)
            return False

        credentials = await self._build_credentials(account)
        if credentials is None:
            logger.warning("refresh_token: no credentials for account %s", email_account_id)
            return False

        try:
            import google.auth.transport.requests as google_requests  # noqa: PLC0415

            request = google_requests.Request()
            credentials.refresh(request)

            if credentials.token:
                account.encrypted_access_token = self._encryption.encrypt(credentials.token)
            if credentials.expiry:
                account.token_expiry = credentials.expiry.replace(tzinfo=timezone.utc)

            await self._session.commit()
            logger.info("Token refreshed for account %s (token: ***)", email_account_id)
            return True
        except Exception:
            logger.exception("Failed to refresh token for account %s", email_account_id)
            return False

    async def get_credentials(self, email_account_id: str) -> Credentials | None:
        """Load and return Google credentials for the given account.

        Args:
            email_account_id: The primary key of the :class:`~app.models.email.EmailAccount`.

        Returns:
            A :class:`~google.oauth2.credentials.Credentials` object, or None if the account
            does not exist or has no refresh token.
        """
        account = await self._get_account_by_id(email_account_id)
        if account is None:
            return None
        return await self._build_credentials(account)

    async def revoke_access(self, email_account_id: str) -> bool:
        """Revoke the OAuth2 tokens and deactivate the account.

        Args:
            email_account_id: The primary key of the :class:`~app.models.email.EmailAccount`.

        Returns:
            True if revocation succeeded; False if the account was not found.
        """
        account = await self._get_account_by_id(email_account_id)
        if account is None:
            logger.warning("revoke_access: account %s not found", email_account_id)
            return False

        try:
            credentials = await self._build_credentials(account)
            if credentials is not None:
                import requests as rq  # noqa: PLC0415

                rq.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": credentials.token or credentials.refresh_token},
                    timeout=10,
                )
        except Exception:
            logger.warning("Could not revoke token remotely for account %s", email_account_id)

        account.encrypted_access_token = None
        account.encrypted_refresh_token = None
        account.token_expiry = None
        account.is_active = False

        await self._session.commit()
        logger.info("Access revoked for account %s", email_account_id)
        return True

    async def list_accounts(self, user_id: str) -> list[EmailAccount]:
        """Return all email accounts linked to the given user.

        Args:
            user_id: The owning user's ID.

        Returns:
            A list of :class:`~app.models.email.EmailAccount` objects (may be empty).
        """
        stmt = select(EmailAccount).where(EmailAccount.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def ensure_valid_token(self, email_account_id: str) -> Credentials | None:
        """Return valid credentials, proactively refreshing if expiry is imminent.

        Access tokens expiring within five minutes are refreshed automatically before
        returning the credentials object.

        Args:
            email_account_id: The primary key of the :class:`~app.models.email.EmailAccount`.

        Returns:
            A valid :class:`~google.oauth2.credentials.Credentials` object, or None if the
            account cannot be found or a refresh attempt fails.
        """
        account = await self._get_account_by_id(email_account_id)
        if account is None:
            return None

        # Proactively refresh if expiring soon
        if account.token_expiry is not None:
            now = datetime.now(timezone.utc)
            expiry = account.token_expiry
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            seconds_remaining = (expiry - now).total_seconds()
            if seconds_remaining < _REFRESH_THRESHOLD_SECONDS:
                logger.info(
                    "Token for account %s expires in %.0fs, refreshing proactively",
                    email_account_id,
                    seconds_remaining,
                )
                refreshed = await self.refresh_token(email_account_id)
                if not refreshed:
                    return None
                # Reload account after refresh
                account = await self._get_account_by_id(email_account_id)
                if account is None:
                    return None

        return await self._build_credentials(account)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_account_by_id(self, email_account_id: str) -> EmailAccount | None:
        """Fetch an EmailAccount by primary key.

        Args:
            email_account_id: UUID primary key.

        Returns:
            The matching :class:`~app.models.email.EmailAccount`, or None.
        """
        stmt = select(EmailAccount).where(EmailAccount.id == email_account_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _build_credentials(self, account: EmailAccount) -> Credentials | None:
        """Construct a Google Credentials object from a stored EmailAccount.

        Args:
            account: The :class:`~app.models.email.EmailAccount` with encrypted tokens.

        Returns:
            A :class:`~google.oauth2.credentials.Credentials` object, or None if the
            account has no refresh token.
        """
        if not account.encrypted_refresh_token:
            return None

        refresh_token = self._encryption.decrypt(account.encrypted_refresh_token)
        access_token: str | None = None
        if account.encrypted_access_token:
            access_token = self._encryption.decrypt(account.encrypted_access_token)

        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=GMAIL_SCOPES,
        )
