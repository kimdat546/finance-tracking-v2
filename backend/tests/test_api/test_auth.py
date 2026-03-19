"""Tests for authentication service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import AuthError, AuthService

USER_EMAIL = "test_auth_user@example.com"
USER_PASSWORD = "securepassword123"
USER_FULLNAME = "Nguyễn Văn Test"


@pytest.fixture
def svc(test_db: AsyncSession) -> AuthService:
    return AuthService(test_db)


@pytest.mark.asyncio
async def test_register_new_user(svc: AuthService) -> None:
    req = RegisterRequest(email=USER_EMAIL, password=USER_PASSWORD, full_name=USER_FULLNAME)
    tokens = await svc.register(req)
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(svc: AuthService) -> None:
    req = RegisterRequest(email="dup@example.com", password=USER_PASSWORD, full_name="Test User")
    await svc.register(req)
    with pytest.raises(AuthError, match="already registered"):
        await svc.register(req)


@pytest.mark.asyncio
async def test_login_success(svc: AuthService) -> None:
    reg = RegisterRequest(email="login@example.com", password=USER_PASSWORD, full_name="Login User")
    await svc.register(reg)

    login = LoginRequest(email="login@example.com", password=USER_PASSWORD)
    tokens = await svc.login(login)
    assert tokens.access_token


@pytest.mark.asyncio
async def test_login_wrong_password_raises(svc: AuthService) -> None:
    reg = RegisterRequest(email="wp@example.com", password=USER_PASSWORD, full_name="WP User")
    await svc.register(reg)

    login = LoginRequest(email="wp@example.com", password="wrongpassword")
    with pytest.raises(AuthError):
        await svc.login(login)


@pytest.mark.asyncio
async def test_refresh_token(svc: AuthService) -> None:
    reg = RegisterRequest(email="refresh@example.com", password=USER_PASSWORD, full_name="Refresh User")
    tokens = await svc.register(reg)
    new_tokens = await svc.refresh(tokens.refresh_token)
    assert new_tokens.access_token
    assert new_tokens.access_token != tokens.access_token


@pytest.mark.asyncio
async def test_decode_access_token(svc: AuthService) -> None:
    user_id = "00000000-0000-0000-0000-000000000001"
    token = AuthService.create_access_token(user_id)
    payload = AuthService.decode_token(token)
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_change_password(svc: AuthService) -> None:
    reg = RegisterRequest(email="chpw@example.com", password=USER_PASSWORD, full_name="CHPW User")
    tokens = await svc.register(reg)
    payload = AuthService.decode_token(tokens.access_token)
    user_id = payload["sub"]

    new_pw = "newpassword456"
    await svc.change_password(user_id, USER_PASSWORD, new_pw)

    # Can now log in with new password
    login = LoginRequest(email="chpw@example.com", password=new_pw)
    new_tokens = await svc.login(login)
    assert new_tokens.access_token
