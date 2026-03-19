"""Pydantic v2 schemas for OAuth2 authorization flow and email account management."""

from datetime import datetime

from pydantic import BaseModel, Field


class OAuthAuthorizeRequest(BaseModel):
    """Request body to initiate a Gmail OAuth2 authorization flow.

    Attributes:
        redirect_uri: The URI Google will redirect the user to after authorization.
            Must match a URI registered in the Google Cloud Console.
    """

    redirect_uri: str = Field(
        default="http://localhost:8000/oauth/callback",
        description="OAuth2 redirect URI registered with Google.",
    )


class OAuthAuthorizeResponse(BaseModel):
    """Response containing the Google authorization URL to redirect the user to.

    Attributes:
        authorization_url: Full URL including state and scope parameters.
        state: Opaque CSRF-protection token to verify on callback.
    """

    authorization_url: str = Field(description="URL to redirect the user to for authorization.")
    state: str = Field(description="CSRF-protection state token.")


class OAuthCallbackRequest(BaseModel):
    """Request body for handling the Google OAuth2 callback.

    Attributes:
        code: Authorization code returned by Google.
        state: State token returned by Google; must match the value sent in the request.
        redirect_uri: Must match the redirect_uri used in the authorization request.
    """

    code: str = Field(description="Authorization code from Google.")
    state: str = Field(description="State token returned by Google callback.")
    redirect_uri: str = Field(
        default="http://localhost:8000/oauth/callback",
        description="The redirect URI used in the original authorization request.",
    )


class OAuthCallbackResponse(BaseModel):
    """Response returned after successfully exchanging an authorization code for tokens.

    Attributes:
        email_account_id: UUID of the newly created or updated EmailAccount record.
        email_address: The Gmail address of the connected account.
        message: Human-readable status message.
    """

    email_account_id: str = Field(description="ID of the linked EmailAccount.")
    email_address: str = Field(description="Gmail address of the connected account.")
    message: str = Field(default="OAuth2 authorization successful.")


class OAuthRefreshRequest(BaseModel):
    """Request body to manually refresh an access token.

    Attributes:
        email_account_id: UUID of the EmailAccount whose token should be refreshed.
    """

    email_account_id: str = Field(description="ID of the EmailAccount to refresh.")


class OAuthRefreshResponse(BaseModel):
    """Response after a successful token refresh.

    Attributes:
        email_account_id: UUID of the refreshed EmailAccount.
        message: Human-readable status message.
        token_expiry: New expiry datetime of the refreshed access token.
    """

    email_account_id: str = Field(description="ID of the refreshed EmailAccount.")
    message: str = Field(default="Token refreshed successfully.")
    token_expiry: datetime | None = Field(default=None, description="New token expiry time.")


class EmailAccountSchema(BaseModel):
    """Public view of an EmailAccount — tokens are never exposed.

    Attributes:
        id: Primary key UUID.
        user_id: Owning user's UUID.
        provider: OAuth provider name (always 'gmail' for now).
        email_address: The linked Gmail address.
        is_active: Whether the account is currently active.
        token_expiry: When the current access token expires (if known).
        last_sync_at: Timestamp of the last successful sync.
        history_id: Gmail historyId used for incremental message sync.
        created_at: Record creation timestamp.
        updated_at: Record last-update timestamp.
    """

    model_config = {"from_attributes": True}

    id: str
    user_id: str
    provider: str
    email_address: str
    is_active: bool
    token_expiry: datetime | None = None
    last_sync_at: datetime | None = None
    history_id: str | None = None
    created_at: datetime
    updated_at: datetime


class OAuthStatusResponse(BaseModel):
    """Response listing all connected email accounts for a user.

    Attributes:
        accounts: List of public EmailAccount representations.
        total: Total number of connected accounts.
    """

    accounts: list[EmailAccountSchema] = Field(
        default_factory=list, description="Connected email accounts."
    )
    total: int = Field(default=0, description="Total number of connected accounts.")
