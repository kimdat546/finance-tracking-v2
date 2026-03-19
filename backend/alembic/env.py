"""Alembic environment configuration with async support."""

import asyncio
import logging
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import all models to ensure they're registered with Base.metadata
from app.database import Base
from app.models import (
    Account,
    Alias,
    Budget,
    Category,
    CategorizationRule,
    Contact,
    Debt,
    DynamicParserSpec,
    Email,
    EmailAccount,
    EmailSyncLog,
    Goal,
    ParserDisabledLog,
    ParserError,
    ParserHealthAlert,
    ParserHealthMetric,
    ParserRegistry,
    ParserVersion,
    SplitBill,
    SplitGroup,
    SplitParticipant,
    Subscription,
    Transaction,
    TransactionGroup,
    TransactionGroupMember,
    UnrecognizedEmail,
    User,
    UserSetting,
)

# This is the Alembic Config object, which provides the values of the
# [alembic] section of the .ini file as Python attributes:
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata

# Override sqlalchemy.url from DATABASE_URL env var if set
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

logger = logging.getLogger("alembic.env")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a database connection.

    Args:
        connection: Database connection
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
