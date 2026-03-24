"""
Task Marketplace Service – post/accept/complete tasks with payments
Aligns with UN SDG 8: Decent Work and Economic Growth

Priority = governing law of execution. Canonical ordering, no bypass.
Dual mode: _priority_locked (audit) + _priority_live (routing).
Execution claim lock: claimed_by, claim_ttl prevent duplicate execution.
"""
# Claim TTL seconds; claim expires if not executed in time.
import os as _os
import time
from collections.abc import Callable

from app.services.priority_routing import compute_priority_score, passes_threshold

CLAIM_TTL_SEC = int(_os.getenv("BRIDGE_CLAIM_TTL_SEC", "300"))


class MarketplaceService:
    def __init__(self):
        self.tasks: list[dict] = []
        self._next_id = 1
        self._seen_pledge_event_ids: set[str] = set()
        self._reputation_getter: Callable[[str], float] | None = None

    def set_reputation_getter(self, fn: Callable[[str], float]) -> None:
        self._reputation_getter = fn

    def _trust_for(self, twin_id: str) -> float:
        if twin_id and self._reputation_getter:
            return self._reputation_getter(twin_id)
        return 0.5

    def get_tasks(self, twin_id: str = "system", status: str | None = None) -> list[dict]:
        """
        Canonical: always sorted by priority. twin_id required (use "system" for neutral).
        No bypass path. Every consumer gets same ordering.
        """
        if status == "all":
            out = list(self.tasks)
        elif status == "in_progress":
            out = [t for t in self.tasks if t.get("status") == "in_progress"]
        elif status == "completed":
            out = [t for t in self.tasks if t.get("status") == "completed"]
        else:
            out = [t for t in self.tasks if t.get("status") == "open"]

        trust = self._trust_for(twin_id)
        now = time.time()
        enriched: list[dict] = []
        for t in out:
            score, inputs = compute_priority_score(t, trust=trust, now_ts=now)
            copy = dict(t)
            copy["_priority_live"] = score
            copy["_priority_score"] = score
            copy["_priority_inputs"] = inputs
            copy["_priority_locked"] = t.get("_priority_locked") or score
            enriched.append(copy)
        enriched.sort(key=lambda x: float(x.get("_priority_score", 0.0)), reverse=True)
        return enriched

    def get_tasks_raw(self, status: str | None = None) -> list[dict]:
        """Tasks without priority enrichment. For async econ scoring in routes."""
        if status == "all":
            return list(self.tasks)
        if status == "in_progress":
            return [t for t in self.tasks if t.get("status") == "in_progress"]
        if status == "completed":
            return [t for t in self.tasks if t.get("status") == "completed"]
        return [t for t in self.tasks if t.get("status") == "open"]

    def get_open_count(self) -> int:
        """Internal: count open tasks without enrichment."""
        return len([t for t in self.tasks if t.get("status") == "open"])

    def get_top_task_for_twin(self, twin_id: str) -> dict | None:
        """Top open task by priority for this twin. None if none pass threshold."""
        tasks = self.get_tasks(twin_id=twin_id, status="open")
        if not tasks:
            return None
        top = tasks[0]
        if not passes_threshold(float(top.get("_priority_score", 0.0))):
            return None
        return top

    def get_task_by_id(self, task_id: int) -> dict | None:
        for t in self.tasks:
            if t.get("id") == task_id:
                return t
        return None

    def add_task(self, task: dict) -> dict:
        task_copy = task.copy()
        task_copy["id"] = self._next_id
        self._next_id += 1
        task_copy.setdefault("status", "open")
        now = time.time()
        task_copy["created_at"] = now
        task_copy.setdefault("urgency", 1.0)
        try:
            task_copy["pledged_total"] = float(task_copy.get("pledged_total", 0) or 0)
        except Exception:
            task_copy["pledged_total"] = 0.0
        score, _inputs = compute_priority_score(task_copy, trust=0.5, now_ts=now)
        task_copy["_priority_locked"] = score
        self.tasks.append(task_copy)
        return task_copy

    def _claim_valid(self, task: dict, node_id: str | None, now: float) -> bool:
        """True if task is unclaimed or claim expired or claimed by this node."""
        claimed = task.get("claimed_by")
        ttl = task.get("claim_ttl") or 0
        if not claimed:
            return True
        if ttl < now:
            return True
        return node_id is not None and claimed == node_id

    def try_claim_task(self, task_id: int, node_id: str) -> dict | None:
        """
        Execution claim lock. Sets claimed_by, claim_ttl.
        Returns task if claim succeeds; None if already claimed and valid.
        """
        task = self.get_task_by_id(task_id)
        if not task or task.get("status") != "open":
            return None
        now = time.time()
        if not self._claim_valid(task, node_id, now):
            return None
        for t in self.tasks:
            if t.get("id") == task_id and t.get("status") == "open":
                t["claimed_by"] = node_id
                t["claim_ttl"] = now + CLAIM_TTL_SEC
                return t
        return None

    def accept_task(self, task_id: int, wallet: str, node_id: str | None = None) -> dict | None:
        """
        Backpressure: reject if task priority < GLOBAL_MIN_PRIORITY.
        Sets execution claim lock (claimed_by, claim_ttl) when accepting.
        """
        task = self.get_task_by_id(task_id)
        if not task or task.get("status") != "open":
            return None
        now = time.time()
        if node_id and not self._claim_valid(task, node_id, now):
            return None
        trust = self._trust_for(wallet.replace("twin:", "")) if "twin:" in wallet else 0.5
        score, _ = compute_priority_score(task, trust=trust)
        if not passes_threshold(score):
            return None
        for t in self.tasks:
            if t.get("id") == task_id and t.get("status") == "open":
                t["acceptor"] = wallet
                t["status"] = "in_progress"
                t["claimed_by"] = node_id or wallet
                t["claim_ttl"] = now + CLAIM_TTL_SEC
                return t
        return None

    def complete_task(self, task_id: int) -> dict | None:
        for t in self.tasks:
            if t.get("id") == task_id and t.get("status") == "in_progress":
                t["status"] = "completed"
                return t
        return None

    def pledge_task(self, task_id: int, wallet: str, amount: float, event_id: str | None = None) -> dict | None:
        if amount is None or amount <= 0:
            return None
        if event_id and event_id in self._seen_pledge_event_ids:
            for t in self.tasks:
                if t.get("id") == task_id:
                    return t
            return None
        for t in self.tasks:
            if t.get("id") == task_id:
                try:
                    t["pledged_total"] = float(t.get("pledged_total", 0) or 0) + float(amount)
                except Exception:
                    t["pledged_total"] = float(amount)
                pledges = t.get("pledges")
                if not isinstance(pledges, list):
                    pledges = []
                pledges.append({"wallet": wallet, "amount": float(amount), "event_id": event_id})
                if len(pledges) > 200:
                    pledges = pledges[-200:]
                t["pledges"] = pledges
                if event_id:
                    self._seen_pledge_event_ids.add(event_id)
                return t
        return None
