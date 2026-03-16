"""
DeFi database — SQLAlchemy 2.0 async.

Dev:  DATABASE_DEFI_URL=sqlite+aiosqlite:///.bridge-state/defi.db
Prod: DATABASE_DEFI_URL=postgresql+asyncpg://user:pass@host/defi
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------
_DEFAULT_SQLITE = (
    Path(__file__).resolve().parents[4]
    / ".bridge-state"
    / "defi.db"
)
_DEFAULT_SQLITE.parent.mkdir(parents=True, exist_ok=True)

DATABASE_DEFI_URL: str = os.environ.get(
    "DATABASE_DEFI_URL",
    f"sqlite+aiosqlite:///{_DEFAULT_SQLITE}",
)

# ---------------------------------------------------------------------------
# Engine + session factory
# ---------------------------------------------------------------------------
_connect_args: dict = {}
if DATABASE_DEFI_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_DEFI_URL,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """Create all tables (idempotent)."""
    from app.defi import models as _  # noqa: F401 — ensure models are imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
