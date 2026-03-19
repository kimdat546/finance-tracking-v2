"""JWT authentication service."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.system import User
from app.models.transaction import Account, Category, Transaction
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
ALGORITHM = "HS256"


class AuthError(Exception):
    """Authentication error."""


class AuthService:
    """Handles user registration, login, and JWT management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Password helpers
    # ------------------------------------------------------------------

    @staticmethod
    def hash_password(plain: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    @staticmethod
    def create_access_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {"sub": user_id, "exp": expire, "type": "access", "jti": secrets.token_hex(16)}
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        # Random jti prevents replay
        payload = {"sub": user_id, "exp": expire, "type": "refresh", "jti": secrets.token_hex(16)}
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate a JWT. Raises AuthError on failure."""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError as exc:
            raise AuthError(f"Invalid token: {exc}") from exc

    def _build_token_response(self, user_id: str) -> TokenResponse:
        access = self.create_access_token(user_id)
        refresh = self.create_refresh_token(user_id)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def register(self, req: RegisterRequest) -> TokenResponse:
        """Register a new user and return tokens."""
        existing = await self.session.execute(
            select(User).where(User.email == req.email)
        )
        if existing.scalar_one_or_none():
            raise AuthError("Email already registered")

        # Derive username from email prefix, ensure uniqueness
        base_username = req.email.split("@")[0][:50]
        username = base_username
        suffix = 1
        while True:
            dup = await self.session.execute(select(User).where(User.username == username))
            if not dup.scalar_one_or_none():
                break
            username = f"{base_username}{suffix}"
            suffix += 1

        parts = req.full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        # schema_name must be unique — use username
        schema_name = f"user_{username}"

        user = User(
            email=req.email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            schema_name=schema_name,
            hashed_password=self.hash_password(req.password),
            is_active=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        # Create a default account
        account = Account(
            user_id=user.id,
            name="Tài khoản chính",
            account_type="checking",
            currency="VND",
            balance=0,
        )
        self.session.add(account)
        await self.session.commit()

        logger.info("Registered new user %s", user.email)
        return self._build_token_response(user.id)

    async def login(self, req: LoginRequest) -> TokenResponse:
        """Validate credentials and return tokens."""
        result = await self.session.execute(
            select(User).where(User.email == req.email, User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        if not user or not self.verify_password(req.password, user.hashed_password or ""):
            raise AuthError("Invalid email or password")

        logger.info("User %s logged in", user.email)
        return self._build_token_response(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Issue new token pair from a valid refresh token."""
        payload = self.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise AuthError("Not a refresh token")
        user_id: str = payload["sub"]
        return self._build_token_response(user_id)

    async def get_user(self, user_id: str) -> User:
        """Fetch user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise AuthError("User not found")
        return user

    @staticmethod
    def get_full_name(user: User) -> str:
        """Return full name from first_name + last_name."""
        parts = [user.first_name or "", user.last_name or ""]
        return " ".join(p for p in parts if p).strip() or user.username

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> None:
        """Change user password after verifying current one."""
        user = await self.get_user(user_id)
        if not self.verify_password(current_password, user.hashed_password or ""):
            raise AuthError("Current password is incorrect")
        user.hashed_password = self.hash_password(new_password)
        await self.session.commit()

    async def delete_account(self, user_id: str, password: str) -> None:
        """GDPR-compliant account deletion — removes all user data."""
        user = await self.get_user(user_id)
        if not self.verify_password(password, user.hashed_password or ""):
            raise AuthError("Password is incorrect")

        # Delete all user data in dependency order
        for model in [Transaction, Account, Category]:
            await self.session.execute(
                delete(model).where(model.user_id == user_id)  # type: ignore[attr-defined]
            )

        await self.session.delete(user)
        await self.session.commit()
        logger.info("Account deleted for user %s", user_id)
