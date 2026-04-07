"""
Supa-Claw vNext — State Engine
================================
Single-writer deterministic persistence core.

Guarantees:
  𝓛₂  GATEKEEPER  — global async mutex, one writer at a time
  𝓛₁  TUNNEL      — serialized commit pipeline (no partial writes)
  𝓛₂₇ EXTENDED    — idempotency keys prevent duplicate commits

Storage: SQLite in WAL mode (strict ACID, readers never block writers).
Drop-in replacement for the file-backed MemoryStore fallback layer.

Schema (single table, Redis-compatible key/value):
  kv(key TEXT PK, value TEXT, updated_at REAL)

Ledger ops use a separate append-only table:
  ledger(id INTEGER PK, key TEXT, entry TEXT, ts REAL)

Idempotency table prevents replay:
  idempotency(idem_key TEXT PK, tx_id TEXT, ts REAL)
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

try:
    import aiosqlite  # type: ignore[import]
except ImportError as _e:  # pragma: no cover
    raise ImportError(
        "aiosqlite is required for StateEngine. Install with: pip install aiosqlite"
    ) from _e

_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS kv (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    key   TEXT    NOT NULL,
    entry TEXT    NOT NULL,
    ts    REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS ledger_key_idx ON ledger(key, id DESC);

CREATE TABLE IF NOT EXISTS idempotency (
    idem_key TEXT PRIMARY KEY,
    tx_id    TEXT NOT NULL,
    ts       REAL NOT NULL
);
"""

# Idempotency window: reject replays within this many seconds (24 h)
_IDEM_TTL = 86_400.0


class StateEngine:
    """
    Transactional key-value + ledger engine backed by SQLite WAL.

    Usage::

        engine = StateEngine(db_path)
        await engine.open()
        ...
        await engine.close()

    All write operations acquire the global async mutex before touching
    the database, ensuring single-writer semantics even under concurrent
    coroutines.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._db: aiosqlite.Connection | None = None
        # 𝓛₂ GATEKEEPER — one writer at a time
        self._write_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._path), check_same_thread=False)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    # ------------------------------------------------------------------
    # KV ops
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Any | None:
        """Return deserialized value at key, or None."""
        db = self._require_db()
        async with db.execute("SELECT value FROM kv WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]

    async def set(self, key: str, value: Any) -> None:
        """Upsert value at key inside a transaction."""
        serialized = json.dumps(value, ensure_ascii=False)
        async with self._write_lock:
            db = self._require_db()
            await db.execute(
                "INSERT INTO kv(key, value, updated_at) VALUES(?,?,?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, serialized, time.time()),
            )
            await db.commit()

    async def delete(self, key: str) -> bool:
        async with self._write_lock:
            db = self._require_db()
            cur = await db.execute("DELETE FROM kv WHERE key = ?", (key,))
            await db.commit()
            return (cur.rowcount or 0) > 0

    async def setnx(self, key: str, value: Any) -> bool:
        """Set only if key absent. Returns True if set, False if already existed."""
        async with self._write_lock:
            db = self._require_db()
            existing = await db.execute("SELECT 1 FROM kv WHERE key = ?", (key,))
            if await existing.fetchone() is not None:
                return False
            await db.execute(
                "INSERT INTO kv(key, value, updated_at) VALUES(?,?,?)",
                (key, json.dumps(value, ensure_ascii=False), time.time()),
            )
            await db.commit()
            return True

    async def incr(self, key: str) -> int:
        """Atomic integer increment."""
        async with self._write_lock:
            db = self._require_db()
            async with db.execute("SELECT value FROM kv WHERE key = ?", (key,)) as cur:
                row = await cur.fetchone()
            try:
                cur_val = int(json.loads(row["value"])) if row else 0
            except Exception:
                cur_val = 0
            new_val = cur_val + 1
            await db.execute(
                "INSERT INTO kv(key, value, updated_at) VALUES(?,?,?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, json.dumps(new_val), time.time()),
            )
            await db.commit()
            return new_val

    # ------------------------------------------------------------------
    # Ledger ops (append-only)
    # ------------------------------------------------------------------

    async def append(self, key: str, entry: Any, *, max_len: int = 500) -> None:
        """Append entry to ledger list at key. Trims to max_len oldest rows."""
        serialized = json.dumps(entry, ensure_ascii=False)
        async with self._write_lock:
            db = self._require_db()
            await db.execute(
                "INSERT INTO ledger(key, entry, ts) VALUES(?,?,?)",
                (key, serialized, time.time()),
            )
            # Trim: delete rows beyond max_len (keep newest)
            await db.execute(
                """DELETE FROM ledger WHERE key = ? AND id NOT IN (
                    SELECT id FROM ledger WHERE key = ? ORDER BY id DESC LIMIT ?
                )""",
                (key, key, max_len),
            )
            await db.commit()

    async def get_recent(self, key: str, n: int = 20) -> list[Any]:
        """Return n most recent entries for key (oldest first)."""
        db = self._require_db()
        async with db.execute(
            "SELECT entry FROM ledger WHERE key = ? ORDER BY id DESC LIMIT ?",
            (key, n),
        ) as cur:
            rows = await cur.fetchall()
        result = []
        for row in reversed(rows):
            try:
                result.append(json.loads(row["entry"]))
            except Exception:
                result.append(row["entry"])
        return result

    # ------------------------------------------------------------------
    # Idempotency (𝓛₂₇ EXTENDED — replay protection)
    # ------------------------------------------------------------------

    async def claim_idempotency(self, idem_key: str, tx_id: str) -> bool:
        """
        Attempt to claim an idempotency slot.
        Returns True  → first time seen, proceed.
        Returns False → duplicate within TTL, skip.
        Expired slots (> _IDEM_TTL) are pruned automatically.
        """
        now = time.time()
        async with self._write_lock:
            db = self._require_db()
            # Prune expired slots
            await db.execute(
                "DELETE FROM idempotency WHERE ts < ?", (now - _IDEM_TTL,)
            )
            async with db.execute(
                "SELECT tx_id FROM idempotency WHERE idem_key = ?", (idem_key,)
            ) as cur:
                existing = await cur.fetchone()
            if existing is not None:
                await db.commit()
                return False
            await db.execute(
                "INSERT INTO idempotency(idem_key, tx_id, ts) VALUES(?,?,?)",
                (idem_key, tx_id, now),
            )
            await db.commit()
            return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _require_db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("StateEngine not open — call await engine.open() first")
        return self._db
