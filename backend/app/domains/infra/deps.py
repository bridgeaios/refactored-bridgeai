"""FastAPI Depends() factories for the infra domain."""
from __future__ import annotations

from app.domains.infra.services import InfraServices

_singleton: InfraServices | None = None


def get_infra() -> InfraServices:
    """Return the singleton InfraServices instance."""
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory
        _singleton = InfraServices(memory=get_memory())
    return _singleton
