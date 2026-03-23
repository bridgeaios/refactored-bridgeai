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

_singleton: EconomyServices | None = None


def get_economy() -> EconomyServices:
    """Return the singleton EconomyServices instance."""
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory
        _singleton = EconomyServices(memory=get_memory())
    return _singleton
