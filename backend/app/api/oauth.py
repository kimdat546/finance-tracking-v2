"""FastAPI router for Gmail OAuth2 authorization and account management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.email import EmailAccount
from app.schemas.oauth import (
    EmailAccountSchema,
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthCallbackResponse,
    OAuthRefreshRequest,
    OAuthRefreshResponse,
    OAuthStatusResponse,
)
from app.services.oauth_service import OAuthService
from app.utils.encryption import EncryptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth")

# ---------------------------------------------------------------------------
# Temporary hard-coded user until WBS-007 implements authentication.
# ---------------------------------------------------------------------------
_TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _get_oauth_service(session: AsyncSession = Depends(get_db)) -> OAuthService:
    """Dependency that builds an :class:`~app.services.oauth_service.OAuthService`.

    Args:
        session: Injected async SQLAlchemy session.

    Returns:
        A fully initialised :class:`~app.services.oauth_service.OAuthService`.

    Raises:
        HTTPException 500: If ENCRYPTION_KEY is not configured.
    """
    try:
        encryption = EncryptionService()
    except ValueError as exc:
        logger.error("ENCRYPTION_KEY not configured: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: ENCRYPTION_KEY is not set.",
        ) from exc
    return OAuthService(session=session, encryption=encryption)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/authorize", response_model=OAuthAuthorizeResponse, summary="Start OAuth2 flow")
async def authorize(
    body: OAuthAuthorizeRequest,
    oauth_svc: OAuthService = Depends(_get_oauth_service),
) -> OAuthAuthorizeResponse:
    """Start a Gmail OAuth2 authorization flow for the current user.

    Returns the Google authorization URL that the client should redirect to.

    Args:
        body: Contains the ``redirect_uri`` for this OAuth2 flow.
        oauth_svc: Injected :class:`~app.services.oauth_service.OAuthService`.

    Returns:
        :class:`~app.schemas.oauth.OAuthAuthorizeResponse` with the authorization URL
        and CSRF state token.

    Raises:
        HTTPException 400: If the authorization URL cannot be generated.
    """
    try:
        auth_url = await oauth_svc.get_authorization_url(
            user_id=_TEST_USER_ID,
            redirect_uri=body.redirect_uri,
        )
    except Exception as exc:
        logger.exception("Failed to generate authorization URL")
        raise HTTPException(status_code=400, detail=f"OAuth error: {exc}") from exc

    # Extract state from the URL query string for the response body
    from urllib.parse import parse_qs, urlparse  # noqa: PLC0415

    parsed = urlparse(auth_url)
    state = parse_qs(parsed.query).get("state", [""])[0]

    return OAuthAuthorizeResponse(authorization_url=auth_url, state=state)


@router.get(
    "/callback",
    response_model=OAuthCallbackResponse,
    summary="Handle Google OAuth2 callback",
)
async def callback(
    code: str = Query(..., description="Authorization code from Google."),
    state: str = Query(..., description="CSRF state token returned by Google."),
    redirect_uri: str = Query(
        default=settings.GOOGLE_REDIRECT_URI,
        description="Must match the redirect URI used during authorization.",
    ),
    oauth_svc: OAuthService = Depends(_get_oauth_service),
) -> OAuthCallbackResponse:
    """Handle the Google OAuth2 redirect callback.

    Exchanges the authorization code for tokens and stores them encrypted.

    Args:
        code: Authorization code returned by Google.
        state: CSRF state token to verify.
        redirect_uri: Must match the URI used in the authorization request.
        oauth_svc: Injected :class:`~app.services.oauth_service.OAuthService`.

    Returns:
        :class:`~app.schemas.oauth.OAuthCallbackResponse` with the new account details.

    Raises:
        HTTPException 400: On invalid state, token exchange failures, or missing email.
    """
    try:
        account: EmailAccount = await oauth_svc.handle_callback(
            user_id=_TEST_USER_ID,
            code=code,
            state=state,
            redirect_uri=redirect_uri,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("OAuth2 callback handling failed")
        raise HTTPException(status_code=400, detail=f"OAuth error: {exc}") from exc

    return OAuthCallbackResponse(
        email_account_id=account.id,
        email_address=account.email_address,
    )


@router.post(
    "/refresh",
    response_model=OAuthRefreshResponse,
    summary="Manually refresh an access token",
)
async def refresh_token(
    body: OAuthRefreshRequest,
    oauth_svc: OAuthService = Depends(_get_oauth_service),
) -> OAuthRefreshResponse:
    """Manually trigger a token refresh for a connected Gmail account.

    Args:
        body: Contains the ``email_account_id`` to refresh.
        oauth_svc: Injected :class:`~app.services.oauth_service.OAuthService`.

    Returns:
        :class:`~app.schemas.oauth.OAuthRefreshResponse` with the new expiry time.

    Raises:
        HTTPException 404: If the account is not found.
        HTTPException 400: If the refresh fails.
    """
    success = await oauth_svc.refresh_token(body.email_account_id)
    if not success:
        # Distinguish "not found" from "refresh error" — both return graceful errors here.
        raise HTTPException(
            status_code=404,
            detail=f"Account {body.email_account_id} not found or token refresh failed.",
        )

    # Reload account to get updated expiry
    credentials = await oauth_svc.get_credentials(body.email_account_id)
    token_expiry = None
    if credentials is not None and credentials.expiry is not None:
        token_expiry = credentials.expiry

    return OAuthRefreshResponse(
        email_account_id=body.email_account_id,
        token_expiry=token_expiry,
    )


@router.delete(
    "/{account_id}",
    status_code=204,
    summary="Revoke OAuth2 access for an account",
)
async def revoke_access(
    account_id: str,
    oauth_svc: OAuthService = Depends(_get_oauth_service),
) -> None:
    """Revoke OAuth2 tokens and deactivate a connected Gmail account.

    Args:
        account_id: UUID of the :class:`~app.models.email.EmailAccount` to revoke.
        oauth_svc: Injected :class:`~app.services.oauth_service.OAuthService`.

    Raises:
        HTTPException 404: If the account is not found.
    """
    success = await oauth_svc.revoke_access(account_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found.")


@router.get(
    "/accounts",
    response_model=OAuthStatusResponse,
    summary="List connected Gmail accounts",
)
async def list_accounts(
    oauth_svc: OAuthService = Depends(_get_oauth_service),
) -> OAuthStatusResponse:
    """Return all Gmail accounts connected to the current user.

    Args:
        oauth_svc: Injected :class:`~app.services.oauth_service.OAuthService`.

    Returns:
        :class:`~app.schemas.oauth.OAuthStatusResponse` with the list of accounts.
    """
    accounts = await oauth_svc.list_accounts(_TEST_USER_ID)
    schemas = [EmailAccountSchema.model_validate(a) for a in accounts]
    return OAuthStatusResponse(accounts=schemas, total=len(schemas))
