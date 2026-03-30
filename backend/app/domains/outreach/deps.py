"""FastAPI Depends() factories for the outreach domain."""
from __future__ import annotations

from app.domains.outreach.services import OutreachService

_singleton: OutreachService | None = None


def get_outreach() -> OutreachService:
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory
        _singleton = OutreachService(memory=get_memory())
    return _singleton
