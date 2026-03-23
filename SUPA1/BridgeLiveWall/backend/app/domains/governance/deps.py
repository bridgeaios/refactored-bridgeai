from __future__ import annotations

from app.domains.governance.services import GovernanceServices

_singleton: GovernanceServices | None = None


def get_governance() -> GovernanceServices:
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory

        _singleton = GovernanceServices(memory=get_memory())
    return _singleton
