"""
Swarm Health — single stability signal for the economy.

Computes a 0–1 score from a small set of observable signals.
This is meant to be simple and robust: if we can't measure something, we
degrade gracefully and avoid false positives.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SwarmHealthComponents:
    queue_latency_ms: float
    worker_utilization: float  # 0–1
    task_profitability: float  # $ profit / task
    agent_failure_rate: float  # 0–1


class SwarmHealthService:
    def __init__(self, telemetry=None):
        self.telemetry = telemetry

    @staticmethod
    def _clamp01(x: float) -> float:
        try:
            return max(0.0, min(1.0, float(x)))
        except Exception:
            return 0.0

    def compute(self, c: SwarmHealthComponents) -> dict:
        """
        Targets (from your spec):
        - queue_latency_ms < 200ms
        - utilization 40–70%
        - profitability > 0.003
        - failure_rate < 1%
        """
        q = float(c.queue_latency_ms or 0.0)
        util = self._clamp01(c.worker_utilization)
        prof = float(c.task_profitability or 0.0)
        fail = self._clamp01(c.agent_failure_rate)

        # Queue latency score: 1.0 at <=200ms, linearly decays to 0 at 2000ms.
        if q <= 200:
            q_score = 1.0
        else:
            q_score = self._clamp01(1.0 - (q - 200.0) / 1800.0)

        # Utilization score: sweet spot 0.4–0.7.
        if 0.4 <= util <= 0.7:
            util_score = 1.0
        elif util < 0.4:
            util_score = self._clamp01(util / 0.4)
        else:
            util_score = self._clamp01(1.0 - (util - 0.7) / 0.3)

        # Profitability score: 1.0 at >=0.003, decays to 0 at 0.
        prof_score = self._clamp01(prof / 0.003) if prof < 0.003 else 1.0

        # Failure score: 1.0 at <=1%, decays to 0 at 10%.
        if fail <= 0.01:
            fail_score = 1.0
        else:
            fail_score = self._clamp01(1.0 - (fail - 0.01) / 0.09)

        # Composite: multiplicative encourages safety throttling.
        health = q_score * util_score * prof_score * fail_score

        return {
            "health_score": round(health, 4),
            "ok": bool(health >= 0.5),
            "targets": {
                "queue_latency_ms": 200,
                "worker_utilization_range": [0.4, 0.7],
                "task_profitability_min": 0.003,
                "agent_failure_rate_max": 0.01,
            },
            "components": {
                "queue_latency_ms": round(q, 2),
                "worker_utilization": round(util, 4),
                "task_profitability": round(prof, 6),
                "agent_failure_rate": round(fail, 4),
                "queue_latency_score": round(q_score, 4),
                "utilization_score": round(util_score, 4),
                "profitability_score": round(prof_score, 4),
                "failure_score": round(fail_score, 4),
            },
        }

