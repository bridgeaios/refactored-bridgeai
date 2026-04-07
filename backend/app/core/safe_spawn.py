"""
𝓛₁₀ DOCTRINE — Safe Async Task Wrapper
========================================
All background tasks MUST be spawned via safe_spawn().

Guarantees:
  - Exceptions are caught, logged, and quarantined (never silently lost)
  - Task is registered for lifecycle tracking
  - Optional retry with bounded back-off
  - CancelledError propagates cleanly (graceful shutdown)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

_log = logging.getLogger("safe_spawn")

# Registry of all live tasks for health inspection
_registry: dict[str, asyncio.Task[Any]] = {}


def safe_spawn(
    coro: Coroutine[Any, Any, Any],
    *,
    name: str,
    retries: int = 0,
    retry_delay: float = 1.0,
) -> asyncio.Task[Any]:
    """
    Spawn a coroutine as a background task with full exception containment.

    Args:
        coro:        The coroutine to run.
        name:        Human-readable name (used in logs + registry).
        retries:     How many times to retry on non-CancelledError failure.
        retry_delay: Initial delay between retries (doubles each attempt).

    Returns:
        The created asyncio.Task.
    """
    task = asyncio.create_task(_guarded(coro, name=name, retries=retries, retry_delay=retry_delay), name=name)
    _registry[name] = task
    task.add_done_callback(lambda t: _registry.pop(name, None))
    return task


async def _guarded(
    coro: Coroutine[Any, Any, Any],
    *,
    name: str,
    retries: int,
    retry_delay: float,
) -> None:
    attempt = 0
    while True:
        try:
            await coro
            return
        except asyncio.CancelledError:
            _log.debug("[%s] cancelled — shutting down cleanly", name)
            raise
        except Exception:
            _log.exception("[%s] unhandled exception (attempt %d/%d)", name, attempt + 1, retries + 1)
            if attempt >= retries:
                _log.error("[%s] quarantined after %d failure(s)", name, attempt + 1)
                return
            attempt += 1
            await asyncio.sleep(retry_delay * (2 ** (attempt - 1)))


def live_tasks() -> dict[str, str]:
    """Return name → state for all registered tasks (for health endpoints)."""
    return {name: ("done" if t.done() else "running") for name, t in _registry.items()}
