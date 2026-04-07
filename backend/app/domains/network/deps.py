"""FastAPI Depends() factories for the network domain."""
from __future__ import annotations

from fastapi import Depends

from app.core.deps import get_memory
from app.domains.network.services import NetworkServices
from app.services.memory_store import MemoryStore


def get_network(mem: MemoryStore = Depends(get_memory)) -> NetworkServices:
    return NetworkServices(memory=mem)
