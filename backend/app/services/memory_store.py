import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from redis.asyncio import from_url

from app.services.state_engine import StateEngine


class MemoryStore:
    def __init__(self) -> None:
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._r: Any | None = None
        # SQLite-backed fallback (WAL, ACID, single-writer via StateEngine mutex).
        # Keep runtime state OUTSIDE the Merkle-hashed code tree.
        # `.bridge-state/` is excluded by the verifier by design.
        repo_root = Path(__file__).resolve().parents[3]
        default_db = repo_root / ".bridge-state" / "runtime" / "state.db"
        db_path = Path(os.getenv("BRIDGE_STATE_DB", str(default_db))).resolve()
        self._engine = StateEngine(db_path)
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        # Open SQLite engine first (always available, no external dep).
        await self._engine.open()
        # Attempt Redis connection; fall back to SQLite if unavailable.
        try:
            r = from_url(self.url, encoding="utf-8", decode_responses=True, socket_connect_timeout=2)
            await r.ping()
            self._r = r
        except Exception:
            self._r = None

    async def disconnect(self) -> None:
        if self._r:
            await self._r.aclose()
        await self._engine.close()

    async def append(self, key: str, value: Any) -> None:
        if self._r:
            await self._r.rpush(key, json.dumps(value))
            return
        max_len = int(os.getenv("BRIDGE_STATE_MAX_LIST_LEN", "500"))
        await self._engine.append(key, value, max_len=max_len)

    async def get_recent(self, key: str, n: int = 20) -> list[Any]:
        if self._r:
            arr = await self._r.lrange(key, -n, -1)
            return [json.loads(x) for x in arr]
        return await self._engine.get_recent(key, n)

    async def get(self, key: str) -> Any:
        """Return the deserialized Python value stored at key, or None if absent."""
        if self._r:
            raw: str | None = await self._r.get(key)
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        return await self._engine.get(key)

    async def set(self, key: str, value: Any) -> bool:
        """Persist value at key. Accepts any JSON-serialisable Python object."""
        if self._r:
            await self._r.set(key, json.dumps(value, ensure_ascii=False))
            return True
        await self._engine.set(key, value)
        return True

    async def incr(self, key: str) -> int:
        """Atomic increment. Monotonic across cluster when using Redis."""
        if self._r:
            result: int = await self._r.incr(key)
            return result
        return await self._engine.incr(key)

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if deleted, False if key did not exist."""
        if self._r:
            deleted: int = await self._r.delete(key)
            return deleted > 0
        return await self._engine.delete(key)

    async def setnx(self, key: str, value: Any) -> bool:
        """Set only if key absent. Returns True if set, False if already existed."""
        if self._r:
            result = await self._r.setnx(key, json.dumps(value, ensure_ascii=False))
            return bool(result)
        return await self._engine.setnx(key, value)

