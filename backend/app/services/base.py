from app.services.memory_store import MemoryStore


class BaseService:
    """Base class for all services with common initialization pattern."""

    def __init__(self, memory: MemoryStore | None = None):
        self.memory = memory or MemoryStore()
