"""FastAPI Depends() factories for the billing domain."""
from __future__ import annotations

from fastapi import Depends

from app.core.deps import get_memory
from app.domains.billing.services import BillingService
from app.services.memory_store import MemoryStore


def get_billing(mem: MemoryStore = Depends(get_memory)) -> BillingService:
    return BillingService(memory=mem)
