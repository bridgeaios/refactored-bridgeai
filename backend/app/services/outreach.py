"""
Thin helper: enqueue an outreach email from any service layer
without taking a direct dependency on OutreachService.

Usage:
    from app.services.outreach import enqueue_outreach
    await enqueue_outreach(memory, {"to": ..., "subject": ..., "body": ..., ...})
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore


async def enqueue_outreach(memory: "MemoryStore", payload: dict[str, Any]) -> dict[str, Any]:
    """Normalise payload keys and enqueue via OutreachService."""
    from app.domains.outreach.services import OutreachService

    # OutreachService uses 'email' key; callers may pass 'to'
    normalised = dict(payload)
    if "to" in normalised and "email" not in normalised:
        normalised["email"] = normalised.pop("to")
    if "name" in normalised and "company" not in normalised:
        normalised.setdefault("company", normalised["name"])

    svc = OutreachService(memory=memory)
    return await svc.enqueue(normalised)
