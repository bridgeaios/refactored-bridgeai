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


def reset_economy_singleton() -> None:
    """Test helper: clear cached EconomyServices."""
    global _singleton
    _singleton = None
