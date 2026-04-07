"""FastAPI Depends() factories for the CRM domain."""
from __future__ import annotations

from fastapi import Depends

from app.core.deps import get_memory
from app.domains.crm.services import CrmService
from app.services.memory_store import MemoryStore


def get_crm(mem: MemoryStore = Depends(get_memory)) -> CrmService:
    return CrmService(memory=mem)
