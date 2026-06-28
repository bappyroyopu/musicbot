"""
Async SQLAlchemy database session management.

Supports both SQLite (via aiosqlite) and PostgreSQL (via asyncpg).
Provides a dependency-injectable async session factory.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from app.config import settings


def _build_engine() -> AsyncEngine:
    """Create the async SQLAlchemy engine based on the configured DATABASE_URL."""
    url = settings.database_url

    if settings.is_sqlite:
        # SQLite: use StaticPool for single-thread sharing, check_same_thread=False
        return create_async_engine(
            url,
            echo=settings.log_level == "DEBUG",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    # PostgreSQL / other: standard async engine with connection pool
    return create_async_engine(
        url,
        echo=settings.log_level == "DEBUG",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


# Module-level singletons
engine: AsyncEngine = _build_engine()

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields a database session.

    Usage::

        async with get_session() as session:
            result = await session.execute(...)
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize the database: create all tables with connection retries.

    Called once during bot startup. Alembic handles migrations for
    production; this function ensures tables exist for fresh installs.
    """
    from app.database.models import Base  # noqa: F401 — import to register all models
    from sqlalchemy.exc import OperationalError, DBAPIError
    import asyncio
    from loguru import logger

    max_retries = 5
    retry_delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Connecting to database (attempt {}/{})...", attempt, max_retries)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database connection established and tables initialized.")
            return
        except (OperationalError, DBAPIError) as e:
            logger.warning("Database connection failed (attempt {}/{}): {}", attempt, max_retries, e)
            if attempt == max_retries:
                logger.error("Could not connect to database after {} attempts.", max_retries)
                raise
            await asyncio.sleep(retry_delay)


async def close_db() -> None:
    """Dispose the engine on shutdown."""
    await engine.dispose()
