"""
Reputation Service — reliability signals for task allocation.

Initial implementation is intentionally lightweight and in-memory, matching the
current marketplace simulation. Persist later (Redis/DB) once the schema stabilizes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Reputation:
    agent_id: str
    completed: int = 0
    failed: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    total_quality: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.completed + self.failed
        return (self.completed / total) if total > 0 else 1.0

    @property
    def average_cost(self) -> float:
        return (self.total_cost / self.completed) if self.completed > 0 else 0.0

    @property
    def latency_ms(self) -> float:
        return (self.total_latency_ms / self.completed) if self.completed > 0 else 0.0

    @property
    def quality_score(self) -> float:
        return (self.total_quality / self.completed) if self.completed > 0 else 0.0

    def score(self) -> float:
        """
        Single composite score (higher is better).
        Bias: reliability > quality > latency > cost.
        """
        sr = self.success_rate
        q = max(0.0, min(1.0, self.quality_score))
        latency_penalty = min(1.0, self.latency_ms / 2000.0)  # 0 at 0ms, 1 at 2s+
        cost_penalty = min(1.0, self.average_cost / 5.0)      # 0 at $0, 1 at $5+
        return max(0.0, (0.55 * sr) + (0.30 * q) + (0.10 * (1.0 - latency_penalty)) + (0.05 * (1.0 - cost_penalty)))


class ReputationService:
    def __init__(self):
        self._rep: dict[str, Reputation] = {}

    def get(self, agent_id: str) -> Reputation:
        if agent_id not in self._rep:
            self._rep[agent_id] = Reputation(agent_id=agent_id)
        return self._rep[agent_id]

    def record_success(
        self,
        agent_id: str,
        *,
        cost: float = 0.0,
        latency_ms: float = 0.0,
        quality: float = 1.0,
    ) -> Reputation:
        r = self.get(agent_id)
        r.completed += 1
        r.total_cost += float(cost or 0.0)
        r.total_latency_ms += float(latency_ms or 0.0)
        r.total_quality += float(quality or 0.0)
        return r

    def record_failure(self, agent_id: str) -> Reputation:
        r = self.get(agent_id)
        r.failed += 1
        return r

    def top(self, limit: int = 20) -> list[dict]:
        ranked = sorted(self._rep.values(), key=lambda r: r.score(), reverse=True)
        out: list[dict] = []
        for r in ranked[: max(1, int(limit or 20))]:
            out.append(self.to_dict(r))
        return out

    @staticmethod
    def to_dict(r: Reputation) -> dict:
        return {
            "agent_id": r.agent_id,
            "completed": r.completed,
            "failed": r.failed,
            "success_rate": round(r.success_rate, 4),
            "average_cost": round(r.average_cost, 4),
            "latency_ms": round(r.latency_ms, 2),
            "quality_score": round(r.quality_score, 4),
            "score": round(r.score(), 4),
        }


_reputation_service: ReputationService | None = None


def get_reputation_service() -> ReputationService:
    global _reputation_service
    if _reputation_service is None:
        _reputation_service = ReputationService()
    return _reputation_service

