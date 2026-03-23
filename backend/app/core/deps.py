"""
Shared FastAPI dependency factories.

Pattern: each factory is decorated with @lru_cache so a single instance
is created per process. Tests override via app.dependency_overrides.

Usage in a route:
    from app.core.deps import get_memory
    @router.get("/status")
    async def status(mem: MemoryStore = Depends(get_memory)):
        ...
"""
from __future__ import annotations

from functools import lru_cache

from app.services.memory_store import MemoryStore


@lru_cache(maxsize=1)
def get_memory() -> MemoryStore:
    """Return the runtime singleton so Depends(get_memory) and direct imports
    from app.runtime share the same connected instance."""
    from app.runtime import memory  # deferred to avoid circular import at module load
    return memory
