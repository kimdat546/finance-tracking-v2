"""Test configuration and fixtures."""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from app.database import Base
from app.main import app
from app.models.system import User
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Test database engine
# ---------------------------------------------------------------------------
# Use PostgreSQL if TEST_DATABASE_URL is set (Docker / CI), else SQLite
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

if TEST_DATABASE_URL:
    # PostgreSQL (Docker)
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
else:
    # SQLite in-memory fallback (fast, but some PG features won't work)
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create event loop for tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with clean tables per test."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session

    # Drop all tables after each test for isolation
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_client() -> TestClient:
    """Create FastAPI test client with test DB dependency override."""
    import asyncio
    from app.database import get_db

    async def _override_get_db():
        async_session_maker = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    # Ensure tables exist
    async def _setup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_setup())

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_id() -> str:
    """Sample user ID for tests."""
    return "00000000-0000-0000-0000-000000000123"


@pytest.fixture
def sample_account_id() -> str:
    """Sample account ID for tests."""
    return "00000000-0000-0000-0000-000000000456"


@pytest.fixture
def sample_category_id() -> str:
    """Sample category ID for tests."""
    return "00000000-0000-0000-0000-000000000789"


# Factory functions for test data
class TransactionFactory:
    """Factory for creating test transactions."""

    @staticmethod
    def build(
        user_id: str = "00000000-0000-0000-0000-000000000001",
        account_id: str = "00000000-0000-0000-0000-000000000002",
        **kwargs,
    ) -> dict:
        """Build transaction data."""
        data = {
            "user_id": user_id,
            "account_id": account_id,
            "amount": kwargs.get("amount", 100.00),
            "currency": kwargs.get("currency", "VND"),
            "type": kwargs.get("type", "expense"),
            "description": kwargs.get("description", "Test transaction"),
            "merchant": kwargs.get("merchant", "Test Merchant"),
            "notes": kwargs.get("notes"),
            "transaction_date": kwargs.get("transaction_date", "2026-03-14"),
            "source": kwargs.get("source", "manual"),
        }
        return data


class AccountFactory:
    """Factory for creating test accounts."""

    @staticmethod
    def build(user_id: str = "00000000-0000-0000-0000-000000000001", **kwargs) -> dict:
        """Build account data."""
        data = {
            "user_id": user_id,
            "name": kwargs.get("name", "Test Account"),
            "account_type": kwargs.get("account_type", "checking"),
            "currency": kwargs.get("currency", "VND"),
            "balance": kwargs.get("balance", 0),
            "institution": kwargs.get("institution", "Test Bank"),
        }
        return data


class CategoryFactory:
    """Factory for creating test categories."""

    @staticmethod
    def build(user_id: str = "00000000-0000-0000-0000-000000000001", **kwargs) -> dict:
        """Build category data."""
        data = {
            "user_id": user_id,
            "name": kwargs.get("name", "Test Category"),
            "transaction_type": kwargs.get("transaction_type", "expense"),
            "icon": kwargs.get("icon"),
            "color": kwargs.get("color"),
        }
        return data


@pytest.fixture
def transaction_factory() -> type:
    """Provide transaction factory."""
    return TransactionFactory


@pytest.fixture
def account_factory() -> type:
    """Provide account factory."""
    return AccountFactory


@pytest.fixture
def category_factory() -> type:
    """Provide category factory."""
    return CategoryFactory


async def create_test_user(
    session: AsyncSession,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    email: str | None = None,
    username: str | None = None,
) -> User:
    """Create and persist a test User record.

    Uses the ``user_id`` to derive unique ``email``, ``username``, and
    ``schema_name`` values so that multiple users can coexist in a single
    test session without violating uniqueness constraints.
    """
    user = User(
        id=user_id,
        email=email or f"user-{user_id}@test.example.com",
        username=username or f"user-{user_id}",
        hashed_password="$2b$12$fakehashfortest",
        schema_name=f"schema_{user_id}",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Provide a default test User record (user_id ending in ...0001)."""
    return await create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000001")
