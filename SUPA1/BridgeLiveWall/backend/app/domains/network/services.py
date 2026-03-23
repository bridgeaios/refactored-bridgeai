"""Network domain service facade (minimal — no separate swarm/projects services in tree)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore


class NetworkServices:
    def __init__(self, memory: "MemoryStore") -> None:
        self._memory = memory

    async def list_projects(self) -> list[dict]:
        return []

    async def register_project(
        self,
        name: str,
        url: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        _ = self._memory
        _ = url
        _ = meta
        return {"ok": True, "project_id": name}

    async def swarm_health(self) -> dict[str, Any]:
        return {"ok": True, "nodes": [], "healthy": True}

    async def swarm_broadcast(
        self,
        channel: str,
        payload: dict,
        sender_id: str = "system",
    ) -> dict[str, Any]:
        _ = sender_id
        return {"ok": True, "channel": channel, "payload": payload}

    async def network_status(self) -> dict[str, Any]:
        health = await self.swarm_health()
        projects = await self.list_projects()
        return {
            "ok": True,
            "swarm": health,
            "projects": len(projects),
        }
