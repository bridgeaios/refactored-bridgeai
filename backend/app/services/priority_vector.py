"""
Multi-Objective Priority — Adaptive, distributed field.

Replaces scalar priority with vector; collapses via governance-controlled weights.
Supports: risk, capital, impact, time-decay, trust decay, anti-gaming.
"""
import math
import os
import time
from collections.abc import Callable
from dataclasses import dataclass

# Governance-controlled weights (env overridable). Collapse: score = sum(plus) - sum(minus)
W_VALUE = float(os.getenv("BRIDGE_PRIORITY_W_VALUE", "0.30"))
W_URGENCY = float(os.getenv("BRIDGE_PRIORITY_W_URGENCY", "0.20"))
W_TRUST = float(os.getenv("BRIDGE_PRIORITY_W_TRUST", "0.20"))
W_IMPACT = float(os.getenv("BRIDGE_PRIORITY_W_IMPACT", "0.15"))
W_RISK = float(os.getenv("BRIDGE_PRIORITY_W_RISK", "0.10"))
W_LATENCY = float(os.getenv("BRIDGE_PRIORITY_W_LATENCY", "0.10"))
W_CAPITAL = float(os.getenv("BRIDGE_PRIORITY_W_CAPITAL", "0.05"))

# Time-decay constants
URGENCY_TAU_HOURS = float(os.getenv("BRIDGE_URGENCY_TAU", "24"))
TRUST_DECAY_TAU_HOURS = float(os.getenv("BRIDGE_TRUST_DECAY_TAU", "72"))

# Risk threshold: block if risk_score > this
RISK_THRESHOLD = float(os.getenv("BRIDGE_RISK_THRESHOLD", "0.8"))

# SDG impact weights by task type (expand via /api/sdg/metrics)
IMPACT_WEIGHTS: dict[str, float] = {
    "marketing": 0.3, "leadgen": 0.4, "analytics": 0.5, "automation": 0.6,
    "frontend": 0.4, "backend": 0.5, "voice": 0.6, "wallet": 0.7, "ubi": 0.9,
    "meta": 0.8, "architecture": 0.8, "general": 0.3,
}


@dataclass
class PriorityVector:
    """Multi-dimensional priority. Collapse to scalar via weighted projection."""
    value: float = 0.0
    urgency: float = 0.0
    trust: float = 0.5
    latency: float = 1.0
    risk: float = 0.0
    impact: float = 0.3
    capital_efficiency: float = 0.0

    def to_scalar(
        self,
        w_value: float = W_VALUE,
        w_urgency: float = W_URGENCY,
        w_trust: float = W_TRUST,
        w_impact: float = W_IMPACT,
        w_risk: float = W_RISK,
        w_latency: float = W_LATENCY,
        w_capital: float = W_CAPITAL,
    ) -> float:
        """score = plus terms - minus terms. Weights are governance-controlled."""
        return (
            w_value * self.value
            + w_urgency * self.urgency
            + w_trust * self.trust
            + w_impact * self.impact
            + w_capital * self.capital_efficiency
            - w_risk * self.risk
            - w_latency * self.latency
        )


def _anti_gaming(x: float) -> float:
    """Prevents reward inflation exploits: log(1 + x)."""
    return math.log1p(max(0.0, float(x)))


def _time_decay_urgency(base: float, age_hours: float, tau: float = URGENCY_TAU_HOURS) -> float:
    """Prevents starvation: urgency = base * exp(-age/tau)."""
    return base * math.exp(-age_hours / max(0.1, tau))


def _trust_decay(trust: float, idle_hours: float, tau: float = TRUST_DECAY_TAU_HOURS) -> float:
    """Trust decay over inactivity. Keeps swarm active."""
    return trust * math.exp(-idle_hours / max(0.1, tau))


def _risk_score(failure_rate: float, variance: float, trust_decay: float) -> float:
    """risk_score = f(failure_rate, variance, trust_decay). Block if > threshold."""
    return min(1.0, failure_rate * 0.5 + variance * 0.3 + (1 - trust_decay) * 0.2)


def _impact_score(task: dict, sdg_getter: Callable[[str], float] | None = None) -> float:
    """Tie into SDG. impact_score = sdg_weight(task_type)."""
    if sdg_getter:
        try:
            t = str(task.get("type", "general"))
            return max(0.1, min(1.0, sdg_getter(t)))
        except Exception:
            pass
    tags = task.get("tags") or []
    task_type = str(task.get("type", "general"))
    for tag in tags:
        tag_lower = str(tag).lower()
        if tag_lower in IMPACT_WEIGHTS:
            return IMPACT_WEIGHTS[tag_lower]
    return IMPACT_WEIGHTS.get(task_type, IMPACT_WEIGHTS["general"])


def _capital_efficiency(reward: float, required_resources: float = 1.0) -> float:
    """Prefer high yield per unit resource."""
    if required_resources <= 0:
        return _anti_gaming(reward)
    return _anti_gaming(reward / required_resources)


def compute_priority_vector(
    task: dict,
    *,
    trust: float = 0.5,
    now_ts: float | None = None,
    idle_hours: float = 0.0,
    failure_rate: float = 0.0,
    variance: float = 0.0,
    required_resources: float = 1.0,
    sdg_getter: Callable[[str], float] | None = None,
) -> tuple[PriorityVector, dict]:
    """
    Build multi-objective priority vector. Returns (vector, raw_inputs).
    Apply to_scalar() for routing. Block if vector.risk > RISK_THRESHOLD.
    """
    now = now_ts or time.time()
    created = task.get("created_at") or task.get("_created_at") or 0
    ts = float(created) if isinstance(created, (int, float)) else 0
    age_hours = max(0.0, (now - ts) / 3600.0) if ts else 0.0

    reward = float(task.get("reward", 0) or 0)
    base_urgency = max(0.0, min(1.0, float(task.get("urgency", 1) or 1)))
    urgency = _time_decay_urgency(base_urgency, age_hours)
    trust_val = min(1.0, max(0.1, trust))
    trust_val = _trust_decay(trust_val, idle_hours)

    latency_cost = max(1.0, age_hours)
    risk_score = _risk_score(failure_rate, variance, trust_val)
    impact = _impact_score(task, sdg_getter)
    capital_eff = _capital_efficiency(reward, required_resources)

    value = _anti_gaming(reward)

    pv = PriorityVector(
        value=value,
        urgency=urgency,
        trust=trust_val,
        latency=_anti_gaming(latency_cost),
        risk=risk_score,
        impact=impact,
        capital_efficiency=capital_eff,
    )

    raw = {
        "reward": reward, "urgency": base_urgency, "trust": trust,
        "latency_cost": round(latency_cost, 4), "risk": round(risk_score, 4),
        "impact": round(impact, 4), "capital_efficiency": round(capital_eff, 4),
    }
    return pv, raw


def passes_risk_threshold(pv: PriorityVector) -> bool:
    """Block execution if risk_score > RISK_THRESHOLD."""
    return pv.risk <= RISK_THRESHOLD
