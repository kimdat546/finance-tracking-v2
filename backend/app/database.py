"""Database configuration and setup."""

from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, Uuid
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DatabaseManager:
    """Manages database engine and session factory."""

    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    def initialize(cls) -> None:
        """Initialize database engine and session factory."""
        cls._engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            poolclass=NullPool if settings.APP_ENV == "test" else None,
        )
        cls._session_factory = async_sessionmaker(
            cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """Get the database engine."""
        if cls._engine is None:
            cls.initialize()
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        """Get the session factory."""
        if cls._session_factory is None:
            cls.initialize()
        return cls._session_factory

    @classmethod
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session as dependency."""
        factory = cls.get_session_factory()
        async with factory() as session:
            yield session

    @classmethod
    async def close(cls) -> None:
        """Close database connections."""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None

    @classmethod
    async def init_db(cls) -> None:
        """Initialize database schema."""
        engine = cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def drop_db(cls) -> None:
        """Drop all database tables. Use with caution!"""
        engine = cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @classmethod
    async def health_check(cls) -> bool:
        """Check database health."""
        try:
            engine = cls.get_engine()
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
                return True
        except Exception:
            return False


# Dependency injection function for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in DatabaseManager.get_session():
        yield session
