from __future__ import annotations

from app.domains.network.services import NetworkServices

_singleton: NetworkServices | None = None


def get_network() -> NetworkServices:
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory

        _singleton = NetworkServices(memory=get_memory())
    return _singleton
