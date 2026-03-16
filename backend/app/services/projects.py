"""
Projects Registry — Bridge AI OS single source of truth for all connected projects.

Any project can register itself at startup via POST /api/projects/register.
The registry tracks live status, capabilities, and metadata for every node in the ecosystem.
"""
from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore

REGISTRY_KEY = "system:projects"


class ProjectsService:
    """Single source of truth registry for all projects in the Bridge AI OS ecosystem."""

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load(self) -> dict[str, Any]:
        raw = await self._memory.get(REGISTRY_KEY)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return {}

    async def _save(self, registry: dict[str, Any]) -> None:
        await self._memory.set(REGISTRY_KEY, json.dumps(registry))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def register(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Register or update a project.
        Required field: id (str).
        Optional: label, type, baseUrl, apiUrl, health, port, capabilities, meta.
        """
        pid = project.get("id")
        if not pid or not isinstance(pid, str):
            raise ValueError("project.id is required")

        registry = await self._load()
        existing = registry.get(pid, {})

        entry: dict[str, Any] = {
            "id": pid,
            "label": project.get("label", existing.get("label", pid)),
            "type": project.get("type", existing.get("type", "service")),
            "baseUrl": project.get("baseUrl", existing.get("baseUrl")),
            "apiUrl": project.get("apiUrl", existing.get("apiUrl")),
            "health": project.get("health", existing.get("health", "/health")),
            "port": project.get("port", existing.get("port")),
            "capabilities": project.get("capabilities", existing.get("capabilities", [])),
            "meta": {**existing.get("meta", {}), **project.get("meta", {})},
            "status": project.get("status", existing.get("status", "online")),
            "registeredAt": existing.get("registeredAt") or _now(),
            "lastSeenAt": _now(),
        }

        registry[pid] = entry
        await self._save(registry)
        return entry

    async def list_projects(self) -> list[dict[str, Any]]:
        registry = await self._load()
        return sorted(registry.values(), key=lambda p: p.get("registeredAt", ""))

    async def get(self, project_id: str) -> dict[str, Any] | None:
        registry = await self._load()
        return registry.get(project_id)

    async def deregister(self, project_id: str) -> bool:
        registry = await self._load()
        if project_id not in registry:
            return False
        del registry[project_id]
        await self._save(registry)
        return True

    async def heartbeat(self, project_id: str, status: str = "online") -> dict[str, Any] | None:
        """Update lastSeenAt and status for a project — call from each project's keep-alive."""
        registry = await self._load()
        if project_id not in registry:
            return None
        registry[project_id]["lastSeenAt"] = _now()
        registry[project_id]["status"] = status
        await self._save(registry)
        return registry[project_id]

    async def seed_from_config(self, config: dict[str, Any]) -> list[str]:
        """
        Auto-register all integratedPlatforms defined in bridge-wall.config.json.
        Called once at startup so the registry is never empty.
        Returns list of seeded project ids.
        """
        platforms: dict[str, Any] = config.get("integratedPlatforms", {})
        seeded: list[str] = []

        # Seed from integratedPlatforms block
        for pid, meta in platforms.items():
            if pid == "description" or not isinstance(meta, dict):
                continue
            project = {
                "id": pid,
                "label": meta.get("label", pid),
                "type": "platform",
                "baseUrl": meta.get("baseUrl"),
                "apiUrl": meta.get("apiUrl"),
                "health": "/health",
                "port": meta.get("port"),
                "capabilities": [],
                "meta": {k: v for k, v in meta.items() if k not in ("label", "baseUrl", "apiUrl", "port")},
                "status": "seeded",
            }
            await self.register(project)
            seeded.append(pid)

        # Seed core BridgeLiveWall services with known ports
        core_services: list[dict[str, Any]] = [
            {"id": "bridge-api", "label": "Bridge API", "type": "api", "baseUrl": "http://localhost:8000", "health": "/health", "port": 8000},
            {"id": "bridge-frontend", "label": "Digital Twin Frontend", "type": "frontend", "baseUrl": "http://localhost:3020", "health": None, "port": 3020},
            {"id": "determinator", "label": "Determinator Boot Agent", "type": "auth", "baseUrl": "http://localhost:4201", "health": None, "port": 4201},
            {"id": "bridge-auth", "label": "Bridge Auth", "type": "auth", "baseUrl": "http://localhost:3030", "health": "/health", "port": 3030},
            {"id": "taurus", "label": "Taurus Showcase", "type": "service", "baseUrl": "http://localhost:4202", "health": "/health", "port": 4202},
        ]
        for svc in core_services:
            pid = str(svc["id"])
            existing = await self.get(pid)
            if not existing:
                await self.register({**svc, "status": "seeded"})
                seeded.append(pid)

        return seeded


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
