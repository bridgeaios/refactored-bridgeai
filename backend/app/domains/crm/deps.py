"""FastAPI Depends() factories for the CRM domain."""
from __future__ import annotations

from app.domains.crm.services import CrmService

_singleton: CrmService | None = None


def get_crm() -> CrmService:
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory
        _singleton = CrmService(memory=get_memory())
    return _singleton
