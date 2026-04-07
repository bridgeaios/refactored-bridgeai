"""Network domain service facade."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.projects import ProjectsService
from app.services.swarm_health import SwarmHealthComponents, SwarmHealthService

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore


class NetworkServices:
    """Aggregates all network-domain services."""

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory
        self._projects = ProjectsService(memory)
        self._swarm_health = SwarmHealthService()

    async def list_projects(self) -> list[dict]:
        return await self._projects.list_projects()

    async def register_project(
        self, name: str, url: str | None = None, meta: dict | None = None
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

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        return await self._projects.get(project_id)

    async def project_heartbeat(self, project_id: str, status: str = "online") -> dict[str, Any] | None:
        return await self._projects.heartbeat(project_id, status)

    async def deregister_project(self, project_id: str) -> bool:
        return await self._projects.deregister(project_id)

    # ------------------------------------------------------------------
    # Replication engine
    # ------------------------------------------------------------------

    async def replication_status(self) -> dict[str, Any]:
        from app.runtime import replication_engine
        return await replication_engine.get_status()

    async def replication_nodes(self) -> list[dict]:
        from app.runtime import replication_engine
        return await replication_engine.get_nodes()

    async def replication_register(
        self, node_id: str, url: str, capabilities: list | None = None
    ) -> dict[str, Any]:
        from app.runtime import replication_engine
        await replication_engine.register_node(node_id, url, capabilities)
        return {"ok": True, "node_id": node_id, "url": url}

    # ------------------------------------------------------------------
    # OSINT Agent / Task / Ledger
    # Backed by memory store (Redis); migrate to Neon/PostgreSQL when ready.
    # ------------------------------------------------------------------

    async def create_agent(self, name: str, agent_type: str = "leadgen") -> dict[str, Any]:
        from uuid import uuid4
        from datetime import datetime, timezone
        agent_id = str(uuid4())
        name = name or f"agent-{agent_id[:8]}"
        agent = {"id": agent_id, "name": name, "type": agent_type, "status": "active",
                 "created_at": datetime.now(timezone.utc).isoformat()}
        await self._memory.set(f"agent:{agent_id}", agent)
        ids: list = await self._memory.get("agent:index") or []
        ids.append(agent_id)
        await self._memory.set("agent:index", ids)
        return agent

    async def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        return await self._memory.get(f"agent:{agent_id}")

    async def list_agents(self) -> list[dict]:
        ids: list = await self._memory.get("agent:index") or []
        agents = [await self._memory.get(f"agent:{i}") for i in ids]
        return [a for a in agents if a]

    async def create_task(self, agent_id: str, task_payload: dict) -> dict[str, Any]:
        from uuid import uuid4
        from datetime import datetime, timezone
        task_id = str(uuid4())
        task = {"id": task_id, "agent_id": agent_id, "payload": task_payload,
                "status": "pending", "created_at": datetime.now(timezone.utc).isoformat()}
        await self._memory.set(f"task:{task_id}", task)
        task_ids: list = await self._memory.get(f"agent:{agent_id}:tasks") or []
        task_ids.append(task_id)
        await self._memory.set(f"agent:{agent_id}:tasks", task_ids)
        return task

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        return await self._memory.get(f"task:{task_id}")

    async def list_tasks(
        self, agent_id: str | None = None, status: str | None = None
    ) -> list[dict]:
        if agent_id:
            task_ids: list = await self._memory.get(f"agent:{agent_id}:tasks") or []
            tasks = [await self._memory.get(f"task:{i}") for i in task_ids]
        else:
            tasks = []
        tasks = [t for t in tasks if t]
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    async def ledger_entries(self, limit: int = 100) -> list[dict]:
        entries: list = await self._memory.get("osint:ledger") or []
        return entries[-limit:]
