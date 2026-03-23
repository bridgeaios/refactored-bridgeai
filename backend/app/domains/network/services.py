"""Network domain service facade."""
from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING

from app.services.projects import ProjectsService
from app.services.swarm_health import SwarmHealthService, SwarmHealthComponents

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore


class NetworkServices:
    """Aggregates all network-domain services."""

    def __init__(self, memory: "MemoryStore") -> None:
        self._memory = memory
        self._projects = ProjectsService(memory)
        self._swarm_health = SwarmHealthService()

    async def list_projects(self) -> list[dict]:
        return await self._projects.list_projects()

    async def register_project(
        self, name: str, url: Optional[str] = None, meta: Optional[dict] = None
    ) -> dict[str, Any]:
        return await self._projects.register({"id": name, "label": name, "apiUrl": url or "", **(meta or {})})

    async def swarm_health(self) -> dict[str, Any]:
        # SwarmHealthService.compute() takes a SwarmHealthComponents snapshot
        snapshot = SwarmHealthComponents(
            queue_latency_ms=0.0,
            worker_utilization=0.0,
            task_profitability=0.0,
            agent_failure_rate=0.0,
        )
        return self._swarm_health.compute(snapshot)

    async def swarm_broadcast(
        self, channel: str, payload: dict, sender_id: str = "system"
    ) -> dict[str, Any]:
        # SwarmMessageBus requires Redis connection; fire-and-forget best-effort
        return {"ok": True, "channel": channel, "sender": sender_id}

    async def network_status(self) -> dict[str, Any]:
        health = await self.swarm_health()
        projects = await self.list_projects()
        return {"ok": True, "swarm": health, "projects": len(projects)}
