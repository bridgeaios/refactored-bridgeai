"""
idempotency.py — Gap 12: Idempotency / Reliability Guarantees.

Every mutating operation gets an idempotency key. The key is stored with:
  - status: pending | committed | failed
  - result: the committed outcome (replayed on duplicate calls)
  - attempt: retry count
  - created_at / committed_at timestamps

Dead-letter queue (DLQ):  tasks that exceed MAX_RETRIES land here.
Retry policy: exponential back-off base 2, cap 300s.

Usage:
    from app.core.idempotency import idempotency_guard, dlq_push, dlq_list

    async with idempotency_guard(mem, key="pay:invoice:42") as guard:
        if guard.already_committed:
            return guard.result        # replay cached outcome
        result = await do_work()
        await guard.commit(result)    # mark committed, cache result
"""
from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

_KEY_PREFIX = "idempotency:"
_DLQ_PREFIX = "dlq:"
_DLQ_INDEX  = "dlq:index"
MAX_RETRIES = 5
RETRY_BASE  = 2      # seconds; delay = min(base ** attempt, 300)
RETRY_CAP   = 300


# ── Core dataclass ──────────────────────────────────────────────────────────

@dataclass
class IdempotencyRecord:
    key: str
    status: str = "pending"       # pending | committed | failed
    result: Any  = None
    attempt: int = 0
    created_at: float = field(default_factory=time.time)
    committed_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "status": self.status,
            "result": self.result,
            "attempt": self.attempt,
            "created_at": self.created_at,
            "committed_at": self.committed_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "IdempotencyRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Guard context manager ────────────────────────────────────────────────────

class _IdempotencyGuard:
    def __init__(self, mem, key: str, record: IdempotencyRecord):
        self._mem    = mem
        self._key    = key
        self._record = record
        self.already_committed = record.status == "committed"
        self.result            = record.result

    async def commit(self, result: Any) -> None:
        self._record.status       = "committed"
        self._record.result       = result
        self._record.committed_at = time.time()
        await self._mem.set(
            _KEY_PREFIX + self._key,
            json.dumps(self._record.to_dict()),
        )

    async def fail(self, reason: str) -> None:
        self._record.status  = "failed"
        self._record.attempt += 1
        self._record.result  = {"error": reason}
        await self._mem.set(
            _KEY_PREFIX + self._key,
            json.dumps(self._record.to_dict()),
        )
        if self._record.attempt >= MAX_RETRIES:
            await dlq_push(self._mem, self._key, reason, self._record.attempt)


@asynccontextmanager
async def idempotency_guard(mem, key: str):
    """
    Context manager that enforces idempotency for a given key.

    On entry:
      - If the key exists and is committed → guard.already_committed = True,
        guard.result = cached result.
      - Otherwise → creates a pending record.

    On exit (no exception) → caller must call guard.commit(result).
    On exception → automatically calls guard.fail(str(exc)).
    """
    raw = await mem.get(_KEY_PREFIX + key)
    if raw:
        try:
            record = IdempotencyRecord.from_dict(json.loads(raw))
        except Exception:
            record = IdempotencyRecord(key=key)
    else:
        record = IdempotencyRecord(key=key)
        await mem.set(_KEY_PREFIX + key, json.dumps(record.to_dict()))

    guard = _IdempotencyGuard(mem, key, record)
    try:
        yield guard
    except Exception as exc:
        if not guard.already_committed:
            await guard.fail(str(exc))
        raise


# ── Dead-letter queue ────────────────────────────────────────────────────────

async def dlq_push(mem, key: str, reason: str, attempt: int) -> None:
    """Push a failed operation key onto the dead-letter queue."""
    entry = {
        "key": key,
        "reason": reason,
        "attempt": attempt,
        "ts": time.time(),
    }
    # Store individual entry
    await mem.set(_DLQ_PREFIX + key, json.dumps(entry))
    # Maintain index list
    index = json.loads(await mem.get(_DLQ_INDEX) or "[]")
    if key not in index:
        index.append(key)
    await mem.set(_DLQ_INDEX, json.dumps(index))


async def dlq_list(mem) -> list[dict]:
    """Return all entries in the dead-letter queue."""
    index = json.loads(await mem.get(_DLQ_INDEX) or "[]")
    entries = []
    for key in index:
        raw = await mem.get(_DLQ_PREFIX + key)
        if raw:
            try:
                entries.append(json.loads(raw))
            except Exception:
                import logging as _log
                _log.getLogger(__name__).warning("[IDEMPOTENCY] corrupt DLQ entry %s — skipped", key)
    return sorted(entries, key=lambda e: e.get("ts", 0), reverse=True)


async def dlq_retry(mem, key: str) -> bool:
    """Remove a key from the DLQ (caller re-executes the operation)."""
    raw = await mem.get(_DLQ_PREFIX + key)
    if not raw:
        return False
    await mem.delete(_DLQ_PREFIX + key)
    index = json.loads(await mem.get(_DLQ_INDEX) or "[]")
    if key in index:
        index.remove(key)
    await mem.set(_DLQ_INDEX, json.dumps(index))
    # Reset idempotency record so the key can re-run
    await mem.set(_KEY_PREFIX + key, json.dumps(IdempotencyRecord(key=key).to_dict()))
    return True


def retry_delay(attempt: int) -> float:
    """Exponential back-off: min(2**attempt, 300) seconds."""
    return min(RETRY_BASE ** attempt, RETRY_CAP)
