"""FastAPI Depends() factories for the outreach domain."""
from __future__ import annotations

from fastapi import Depends

from app.core.deps import get_memory
from app.domains.outreach.services import OutreachService
from app.services.memory_store import MemoryStore


def get_outreach(mem: MemoryStore = Depends(get_memory)) -> OutreachService:
    return OutreachService(memory=mem)
