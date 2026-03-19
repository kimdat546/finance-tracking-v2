"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_user_id_from_header(authorization: str = Header(default="")) -> str:
    """Extract bearer token and decode user_id.

    In production this would be a proper dependency that raises 401.
    For now it gracefully falls back to a test user.
    """
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            from app.services.auth_service import AuthService
            payload = AuthService.decode_token(token)
            return payload["sub"]
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
    # Dev fallback
    return "00000000-0000-0000-0000-000000000001"


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    req: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user."""
    svc = AuthService(session)
    try:
        return await svc.register(req)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return JWT token pair."""
    svc = AuthService(session)
    try:
        return await svc.login(req)
    except AuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    req: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Obtain a new token pair from a valid refresh token."""
    svc = AuthService(session)
    try:
        return await svc.refresh(req.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(_get_user_id_from_header),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Return the current authenticated user's profile."""
    svc = AuthService(session)
    try:
        user = await svc.get_user(user_id)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    full_name = AuthService.get_full_name(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=full_name,
        is_active=user.is_active,
    )


@router.post("/change-password", status_code=204)
async def change_password(
    req: ChangePasswordRequest,
    user_id: str = Depends(_get_user_id_from_header),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Change the authenticated user's password."""
    svc = AuthService(session)
    try:
        await svc.change_password(user_id, req.current_password, req.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/account", status_code=204)
async def delete_account(
    req: DeleteAccountRequest,
    user_id: str = Depends(_get_user_id_from_header),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete the authenticated user's account and all data (GDPR)."""
    if not req.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to delete account",
        )
    svc = AuthService(session)
    try:
        await svc.delete_account(user_id, req.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
