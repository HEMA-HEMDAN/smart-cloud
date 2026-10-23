"""Database session management using SQLAlchemy 2.x async engine."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Module-level engine and session factory (initialised in lifespan)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine not initialised. Call init_db first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Call init_db first.")
    return _session_factory


async def init_db() -> None:
    """Create the async engine and session factory."""
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url_async,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=settings.environment == "development",
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    logger.info("database.engine.created", host=settings.db_host, db=settings.db_name)


async def close_db() -> None:
    """Dispose the engine on shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("database.engine.disposed")


@asynccontextmanager
async def db_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ANN001
    """FastAPI lifespan context manager – startup and shutdown."""
    await init_db()
    from app.db.qdrant import close_qdrant, init_qdrant

    await init_qdrant()
    yield
    await close_db()
    await close_qdrant()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
