"""
Shared FastAPI dependency factories.

Uses the process-wide MemoryStore from app.runtime so lifespan, routes, and
tests share one instance (avoids split-brain state).
"""
from __future__ import annotations

from app.services.memory_store import MemoryStore


def get_memory() -> MemoryStore:
    """Return the singleton MemoryStore from runtime."""
    from app.runtime import memory

    return memory
