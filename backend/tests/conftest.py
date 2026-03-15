"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings
from app.database import Base, DatabaseManager
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create event loop for tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    # Use in-memory SQLite for tests
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=None,
    )

    # Create tables
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

    # Cleanup
    await test_engine.dispose()


@pytest.fixture
def test_client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_user_id() -> str:
    """Sample user ID for tests."""
    return "test-user-123"


@pytest.fixture
def sample_account_id() -> str:
    """Sample account ID for tests."""
    return "test-account-456"


@pytest.fixture
def sample_category_id() -> str:
    """Sample category ID for tests."""
    return "test-category-789"


# Factory functions for test data
class TransactionFactory:
    """Factory for creating test transactions."""

    @staticmethod
    def build(
        user_id: str = "test-user",
        account_id: str = "test-account",
        **kwargs,
    ) -> dict:
        """Build transaction data.

        Args:
            user_id: User ID
            account_id: Account ID
            **kwargs: Additional fields

        Returns:
            Transaction data dictionary
        """
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
    def build(user_id: str = "test-user", **kwargs) -> dict:
        """Build account data.

        Args:
            user_id: User ID
            **kwargs: Additional fields

        Returns:
            Account data dictionary
        """
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
    def build(user_id: str = "test-user", **kwargs) -> dict:
        """Build category data.

        Args:
            user_id: User ID
            **kwargs: Additional fields

        Returns:
            Category data dictionary
        """
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
