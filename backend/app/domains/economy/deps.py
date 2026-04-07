"""
FastAPI Depends() factories for the economy domain.

Usage:
    from app.domains.economy.deps import get_economy
    @router.post("/treasury/collect")
    async def collect(svc: EconomyServices = Depends(get_economy)):
        ...
"""
from __future__ import annotations

from app.domains.economy.services import EconomyServices

from app.core.deps import get_memory
from app.services.memory_store import MemoryStore
from fastapi import Depends


def get_economy(mem: MemoryStore = Depends(get_memory)) -> EconomyServices:
    """Return an EconomyServices instance backed by the injected MemoryStore.

    Using Depends(get_memory) means test overrides of get_memory propagate here
    automatically — no singleton caching needed.
    """
    return EconomyServices(memory=mem)
