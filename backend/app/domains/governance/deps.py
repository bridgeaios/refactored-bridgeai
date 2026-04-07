"""FastAPI Depends() factories for the governance domain."""
from __future__ import annotations

from fastapi import Depends

from app.core.deps import get_memory
from app.domains.governance.services import GovernanceServices
from app.services.memory_store import MemoryStore


def get_governance(mem: MemoryStore = Depends(get_memory)) -> GovernanceServices:
    return GovernanceServices(memory=mem)
