"""FastAPI Depends() factories for the billing domain."""
from __future__ import annotations

from app.domains.billing.services import BillingService

_singleton: BillingService | None = None


def get_billing() -> BillingService:
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory
        _singleton = BillingService(memory=get_memory())
    return _singleton
