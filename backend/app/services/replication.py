"""
Replication Engine — Self-expanding AI network (SELF-EXPANDING-AI-NETWORK.md, GLOBAL-TWIN-SWARM-ARCHITECTURE.md).

Rules:
- If task demand > agent capacity → create new twin (auto_add task and/or register_twin).
- If twin performance > threshold → spawn variant twin (register_twin with variant name).

Status is stored in memory (replication:status) for GET /api/replication/status.
"""

import os
import time
from typing import Any


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


class ReplicationEngine:
    """Evaluates replication rules and triggers auto_add / register_twin."""

    STATUS_KEY = "replication:status"
    NODES_KEY = "replication:nodes"

    def __init__(self, memory, twins, marketplace):
        self.memory = memory
        self.twins = twins
        self.marketplace = marketplace
        self.enabled = os.getenv("BRIDGE_REPLICATION", "1") not in ("0", "false", "False")
        self.demand_per_twin = _env_int("BRIDGE_REPLICATION_DEMAND_PER_TWIN", 3)
        self.performance_threshold = _env_int("BRIDGE_REPLICATION_PERFORMANCE_THRESHOLD", 5)
        self._last_status: dict[str, Any] = {}

    def _twin_count(self) -> int:
        return len(getattr(self.twins, "twins", {}))

    def _open_task_count(self) -> int:
        return self.marketplace.get_open_count()

    def _best_twin_id_for_variant(self) -> str | None:
        """Twin with highest completed count above threshold."""
        leaderboard = self.twins.get_leaderboard()
        for e in leaderboard:
            if e.get("completed", 0) >= self.performance_threshold:
                return e.get("id")
        return None

    def _next_variant_name(self) -> str:
        """Generate next twin variant name (delta, epsilon, zeta, ...)."""
        greek = ["delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa", "lambda"]
        existing = {t.id for t in getattr(self.twins, "twins", {}).values()}
        for name in greek:
            if name not in existing:
                return name
        return f"twin_{len(existing) + 1}"

    async def evaluate(self) -> dict[str, Any]:
        """Run replication rules once. Returns status dict and persists to memory."""
        if not self.enabled:
            return {"enabled": False, "message": "replication disabled"}

        now = time.time()
        open_tasks = self._open_task_count()
        twin_count = self._twin_count()
        capacity = twin_count * self.demand_per_twin
        twins_created = 0
        tasks_added = 0
        rules_evaluated = []

        # Rule 1: task demand > agent capacity → add task and optionally create new twin
        if open_tasks > capacity or (open_tasks > 0 and twin_count < 3):
            rules_evaluated.append("demand_over_capacity")
            try:
                task = self.twins.auto_add_task(self.marketplace)
                if task:
                    tasks_added += 1
            except Exception:
                pass
            # If still under capacity, register a new twin (variant)
            if twin_count < 5 and open_tasks > twin_count * max(1, self.demand_per_twin - 1):
                try:
                    name = self._next_variant_name()
                    self.twins.register_twin(name, name.capitalize() + " Twin")
                    twins_created += 1
                    rules_evaluated.append("new_twin_registered")
                except Exception:
                    pass

        # Rule 2: twin performance > threshold → spawn variant twin
        best = self._best_twin_id_for_variant()
        if best and twin_count < 8:
            rules_evaluated.append("performance_spawn_variant")
            try:
                name = self._next_variant_name()
                if name not in getattr(self.twins, "twins", {}):
                    self.twins.register_twin(name, name.capitalize() + " Twin")
                    twins_created += 1
            except Exception:
                pass

        status = {
            "enabled": self.enabled,
            "last_run_at": now,
            "open_tasks": open_tasks,
            "twin_count": twin_count,
            "capacity": capacity,
            "demand_per_twin": self.demand_per_twin,
            "performance_threshold": self.performance_threshold,
            "twins_created_this_run": twins_created,
            "tasks_added_this_run": tasks_added,
            "rules_evaluated": rules_evaluated,
        }
        self._last_status = status
        try:
            import json
            await self.memory.set(self.STATUS_KEY, json.dumps(status))
        except Exception:
            pass
        return status

    async def get_status(self) -> dict[str, Any]:
        """Return last replication status (from memory or last run)."""
        if self._last_status:
            return self._last_status
        try:
            import json
            raw = await self.memory.get(self.STATUS_KEY)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return {
            "enabled": self.enabled,
            "last_run_at": None,
            "open_tasks": self._open_task_count(),
            "twin_count": self._twin_count(),
            "capacity": self._twin_count() * self.demand_per_twin,
            "demand_per_twin": self.demand_per_twin,
            "performance_threshold": self.performance_threshold,
            "twins_created_this_run": 0,
            "tasks_added_this_run": 0,
            "rules_evaluated": [],
        }

    async def register_node(self, node_id: str, url: str, capabilities: list[str] | None = None) -> None:
        """Register this or a peer node for discovery (store in memory)."""
        import json
        nodes = await self.get_nodes()
        nodes = [n for n in nodes if n.get("node_id") != node_id]
        nodes.append({
            "node_id": node_id,
            "url": url.rstrip("/"),
            "capabilities": capabilities or [],
            "registered_at": time.time(),
        })
        await self.memory.set(self.NODES_KEY, json.dumps(nodes))

    async def get_nodes(self) -> list[dict[str, Any]]:
        """Return list of registered nodes (for mesh discovery)."""
        try:
            raw = await self.memory.get(self.NODES_KEY)
            if raw:
                import json
                return json.loads(raw)
        except Exception:
            pass
        return []
