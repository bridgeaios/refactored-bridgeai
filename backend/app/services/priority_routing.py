"""
Priority Routing — Universal routing function for Bridge AI OS.

Legacy: priority_score = (reward * urgency * trust) / max(1, latency_cost)
Vector: multi-objective priority with weighted projection (see priority_vector).

Governing law of execution. No bypass. Canonical ordering.
"""
import os
import time
from collections.abc import Callable

# Global backpressure. Apply to accept, allocate, demand/pump.
# Set via env: BRIDGE_PRIORITY_MIN_THRESHOLD
GLOBAL_MIN_PRIORITY = float(os.getenv("BRIDGE_PRIORITY_MIN_THRESHOLD", "0.15"))
MIN_THRESHOLD = GLOBAL_MIN_PRIORITY  # Alias

# Target for demand pump: throttle creation if avg above this.
TARGET_PRIORITY = float(os.getenv("BRIDGE_TARGET_PRIORITY", "2.0"))

# Use vector priority when True (multi-objective, governance weights).
USE_VECTOR_PRIORITY = os.getenv("BRIDGE_USE_VECTOR_PRIORITY", "false").lower() in ("1", "true", "yes")


def normalize_trust(reputation: float) -> float:
    """Prevent exploit: clamp to [0.1, 1.0]. Avoids runaway dominance and zero-trust deadlock."""
    return min(1.0, max(0.1, float(reputation)))


def get_latency_cost(
    task: dict,
    *,
    telemetry_getter: Callable[[str], float] | None = None,
    now_ts: float | None = None,
) -> float:
    """
    Latency cost for priority. Prefer telemetry by task type; else task age.
    """
    if telemetry_getter:
        task_type = str(task.get("type", "general"))
        try:
            avg = telemetry_getter(task_type)
            if avg and avg > 0:
                return max(1.0, avg)
        except Exception:
            pass
    created = task.get("created_at") or task.get("_created_at") or 0
    ts = float(created) if isinstance(created, (int, float)) else 0
    now = now_ts if now_ts is not None else time.time()
    age_hours = max(0.0, (now - ts) / 3600.0) if ts else 0.0
    return max(1.0, age_hours)


def compute_priority_score(
    task: dict,
    *,
    trust: float = 0.5,
    now_ts: float | None = None,
    latency_cost: float | None = None,
    telemetry_getter: Callable[[str], float] | None = None,
    idle_hours: float = 0.0,
    failure_rate: float = 0.0,
    variance: float = 0.0,
    required_resources: float = 1.0,
    sdg_getter: Callable[[str], float] | None = None,
) -> tuple[float, dict]:
    """
    Returns (score, inputs_dict) for audit.
    When USE_VECTOR_PRIORITY: multi-objective weighted projection; risk blocks if > threshold.
    Else: legacy (reward * urgency * trust) / max(1, latency_cost).
    """
    if USE_VECTOR_PRIORITY:
        from app.services.priority_vector import (
            RISK_THRESHOLD,
            compute_priority_vector,
            passes_risk_threshold,
        )
        pv, raw = compute_priority_vector(
            task,
            trust=trust,
            now_ts=now_ts,
            idle_hours=idle_hours,
            failure_rate=failure_rate,
            variance=variance,
            required_resources=required_resources,
            sdg_getter=sdg_getter,
        )
        if not passes_risk_threshold(pv):
            return 0.0, {**raw, "blocked_by_risk": True, "risk_threshold": RISK_THRESHOLD}
        score = max(0.0, pv.to_scalar())
        inputs = {**raw, "score": round(score, 4)}
        return round(score, 4), inputs

    reward = float(task.get("reward", 0) or 0)
    urgency = max(0.0, min(1.0, float(task.get("urgency", 1) or 1)))
    trust_val = normalize_trust(trust)
    if latency_cost is not None:
        lc = max(1.0, float(latency_cost))
    else:
        lc = get_latency_cost(task, telemetry_getter=telemetry_getter, now_ts=now_ts)
    num = reward * urgency * trust_val
    score = num / lc if lc > 0 else num

    inputs = {
        "reward": reward,
        "urgency": urgency,
        "trust": trust_val,
        "latency_cost": round(lc, 4),
    }
    return round(score, 4), inputs


def passes_threshold(score: float) -> bool:
    """Backpressure: score >= GLOBAL_MIN_PRIORITY."""
    return score >= GLOBAL_MIN_PRIORITY
