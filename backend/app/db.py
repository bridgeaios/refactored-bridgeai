"""
Unified database connection — SQLAlchemy 2.0 async.

Provides:
  - Async engine with connection pooling (production-ready defaults)
  - Async session factory
  - Dependency for FastAPI (get_db)
  - Health check function (check_db_health)

Env vars:
  DATABASE_URL  — required.  e.g. postgresql+asyncpg://user:pass@host:5432/bridge_unified
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    logger.warning("DATABASE_URL not set — database operations will fail at runtime.")

# Normalise URL for asyncpg driver
_url = DATABASE_URL
if _url.startswith("postgresql://") or _url.startswith("postgres://"):
    _url = "postgresql+asyncpg://" + _url.split("://", 1)[1]

# ---------------------------------------------------------------------------
# Engine with production pooling
# ---------------------------------------------------------------------------
_engine_kwargs: dict[str, Any] = {
    "echo": os.environ.get("SQL_ECHO", "").lower() in ("1", "true"),
    "future": True,
}

if _url and "asyncpg" in _url:
    _engine_kwargs.update(
        pool_size=int(os.environ.get("DB_POOL_SIZE", "10")),
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.environ.get("DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "1800")),
        pool_pre_ping=True,
    )

engine: AsyncEngine | None = None
if _url:
    engine = create_async_engine(_url, **_engine_kwargs)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None
if engine is not None:
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# ---------------------------------------------------------------------------
# Declarative base (shared across all domain models if needed)
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session; rolls back on unhandled error."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not configured — set DATABASE_URL")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
async def check_db_health() -> dict[str, Any]:
    """
    Run a lightweight query to verify the database is reachable.
    Returns {"ok": True/False, "latency_ms": ..., "error": ...}.
    """
    import time

    if engine is None:
        return {"ok": False, "error": "DATABASE_URL not configured"}

    t0 = time.monotonic()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = round((time.monotonic() - t0) * 1000, 2)
        return {"ok": True, "latency_ms": latency}
    except Exception as exc:
        latency = round((time.monotonic() - t0) * 1000, 2)
        return {"ok": False, "latency_ms": latency, "error": str(exc)}


# ---------------------------------------------------------------------------
# Table creation helper (for dev / testing)
# ---------------------------------------------------------------------------
async def create_all_tables() -> None:
    """Create all tables registered on Base.metadata (idempotent)."""
    if engine is None:
        raise RuntimeError("Database not configured — set DATABASE_URL")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
