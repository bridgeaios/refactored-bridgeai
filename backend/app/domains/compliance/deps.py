"""FastAPI Depends() factories for the Compliance domain."""
from __future__ import annotations

from fastapi import Depends

from app.core.deps import get_memory
from app.domains.compliance.services import ComplianceService
from app.services.memory_store import MemoryStore


def get_compliance(mem: MemoryStore = Depends(get_memory)) -> ComplianceService:
    return ComplianceService(memory=mem)
