import asyncio
import json
import os
from pathlib import Path
from typing import Any

from redis.asyncio import from_url


class MemoryStore:
    def __init__(self) -> None:
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._r: Any | None = None
        # File-backed fallback so the system remains stateful without Redis/Docker.
        # Keep runtime state OUTSIDE the Merkle-hashed code tree.
        # `.bridge-state/` is excluded by the verifier by design.
        repo_root = Path(__file__).resolve().parents[3]
        default_file = repo_root / ".bridge-state" / "runtime" / "memory_store.json"
        self._file_path = Path(os.getenv("BRIDGE_STATE_FILE", str(default_file))).resolve()
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        try:
            r = from_url(self.url, encoding="utf-8", decode_responses=True, socket_connect_timeout=2)
            await r.ping()
            self._r = r
        except Exception:
            self._r = None
        # Always initialize file store (even if Redis is up, used for bootstrap/dev fallback).
        await self._ensure_file()

    async def disconnect(self) -> None:
        if self._r:
            await self._r.aclose()

    async def _ensure_file(self) -> None:
        # IMPORTANT: do not take self._lock here.
        # Callers already guard critical sections with self._lock, and re-entrant lock
        # would deadlock during startup (e.g., verify_boot_identity -> memory.get()).
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            if not self._file_path.exists():
                self._file_path.write_text("{}", encoding="utf-8")
        except Exception:
            # Best-effort fallback.
            pass

    async def _read_file_state(self) -> dict[str, Any]:
        await self._ensure_file()
        try:
            raw = self._file_path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    async def _write_file_state(self, state: dict) -> None:
        await self._ensure_file()
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file_path.with_suffix(self._file_path.suffix + ".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, ensure_ascii=False)
        tmp.write_text(payload, encoding="utf-8")
        if not tmp.exists():
            raise FileNotFoundError(f"temporary state file was not created: {tmp}")
        os.replace(tmp, self._file_path)

    async def append(self, key: str, value: Any) -> None:
        if self._r:
            await self._r.rpush(key, json.dumps(value))
            return
        async with self._lock:
            state = await self._read_file_state()
            arr = state.get(key)
            if not isinstance(arr, list):
                arr = []
            arr.append(value)
            # Prevent unbounded growth.
            max_len = int(os.getenv("BRIDGE_STATE_MAX_LIST_LEN", "500"))
            if max_len > 0 and len(arr) > max_len:
                arr = arr[-max_len:]
            state[key] = arr
            await self._write_file_state(state)

    async def get_recent(self, key: str, n: int = 20) -> list[Any]:
        if self._r:
            arr = await self._r.lrange(key, -n, -1)
            return [json.loads(x) for x in arr]
        async with self._lock:
            state = await self._read_file_state()
            arr = state.get(key)
            if not isinstance(arr, list):
                return []
            return arr[-n:]

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
        async with self._lock:
            state = await self._read_file_state()
            val = state.get(key)
            if val is None:
                return None
            # File backend already stores parsed objects; return as-is.
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    return val
            return val

    async def set(self, key: str, value: Any) -> bool:
        """Persist value at key. Accepts any JSON-serialisable Python object."""
        if self._r:
            await self._r.set(key, json.dumps(value, ensure_ascii=False))
            return True
        async with self._lock:
            state = await self._read_file_state()
            state[key] = value
            await self._write_file_state(state)
            return True

    async def incr(self, key: str) -> int:
        """Atomic increment. Monotonic across cluster when using Redis."""
        if self._r:
            result: int = await self._r.incr(key)
            return result
        async with self._lock:
            state = await self._read_file_state()
            cur = state.get(key)
            try:
                cur_i = int(cur) if cur is not None else 0
            except Exception:
                cur_i = 0
            cur_i += 1
            state[key] = cur_i
            await self._write_file_state(state)
            return cur_i

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if deleted, False if key did not exist."""
        if self._r:
            deleted: int = await self._r.delete(key)
            return deleted > 0
        async with self._lock:
            state = await self._read_file_state()
            if key not in state:
                return False
            del state[key]
            await self._write_file_state(state)
            return True

    async def setnx(self, key: str, value: Any) -> bool:
        """Set key to value only if key does not already exist.
        Returns True if the key was set, False if it already existed (claim failed).
        On Redis this is atomic; on the file backend it is protected by the async lock.
        """
        if self._r:
            serialized = json.dumps(value, ensure_ascii=False)
            result = await self._r.setnx(key, serialized)
            return bool(result)
        async with self._lock:
            state = await self._read_file_state()
            if key in state:
                return False
            state[key] = value
            await self._write_file_state(state)
            return True

