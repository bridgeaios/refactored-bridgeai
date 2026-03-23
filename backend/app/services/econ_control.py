"""Economic Control Kernel - Single invariant pipeline. Weights = w. Score = w dot P."""
from __future__ import annotations
import json
import math
import time
from dataclasses import dataclass
from typing import Callable, Optional

DEFAULT_WEIGHTS = {"impact": 0.20, "revenue": 0.30, "risk": -0.15, "latency": -0.15, "trust": 0.20}
MEMORY_KEY_WEIGHTS = "econ:weights"

@dataclass
class PriorityComponents:
    impact: float = 0.0
    revenue: float = 0.0
    risk: float = 0.0
    latency: float = 1.0
    trust: float = 0.5

def _dot(w, p):
    return w.get("impact",0)*p.impact + w.get("revenue",0)*p.revenue + w.get("risk",0)*p.risk + w.get("latency",0)*p.latency + w.get("trust",0)*p.trust

class EconControlService:
    def __init__(self, memory=None):
        self._memory = memory
        self._weights = dict(DEFAULT_WEIGHTS)
        self._reputation_getter = None

    def set_reputation_getter(self, fn): self._reputation_getter = fn

    async def _load_weights(self):
        if self._memory:
            raw = await self._memory.get(MEMORY_KEY_WEIGHTS)
            if raw:
                try:
                    data = json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(data, dict): self._weights = {**DEFAULT_WEIGHTS, **data}
                except Exception: pass
        return self._weights.copy()

    async def _save_weights(self, w):
        self._weights = {**DEFAULT_WEIGHTS, **w}
        if self._memory: await self._memory.set(MEMORY_KEY_WEIGHTS, json.dumps(self._weights))

    async def get_weights(self): await self._load_weights(); return self._weights.copy()

    async def set_weights(self, w):
        valid = {k: float(v) for k, v in w.items() if k in DEFAULT_WEIGHTS}
        await self._save_weights(valid)
        return await self.get_weights()

    def risk_budget(self, twin_id):
        trust = 0.5
        if self._reputation_getter: trust = max(0.1, min(1.0, self._reputation_getter(twin_id)))
        return 0.3 + 0.7 * trust

    def capital_assigned(self, twin_id):
        trust = 0.5
        if self._reputation_getter: trust = max(0.1, min(1.0, self._reputation_getter(twin_id)))
        return 10.0 + 90.0 * trust

    def capital_required(self, task):
        reward = float(task.get("reward",0) or 0)
        pledged = float(task.get("pledged_total",0) or 0)
        return max(0.5, reward * 0.5 + pledged * 0.1)

    def build_p(self, task, twin_id, now_ts=None):
        now = now_ts or time.time()
        reward = float(task.get("reward",0) or 0)
        urgency = max(0.0, min(1.0, float(task.get("urgency",1) or 1)))
        created = task.get("created_at") or task.get("_created_at") or 0
        ts = float(created) if isinstance(created, (int,float)) else 0
        age_hours = max(0.0, (now - ts) / 3600.0) if ts else 0.0
        trust = 0.5
        if twin_id and self._reputation_getter: trust = max(0.1, min(1.0, self._reputation_getter(twin_id)))
        latency = max(0.1, math.log1p(age_hours))
        risk = min(1.0, (1 - trust) * 0.6)
        impact = 0.5
        tags = task.get("tags") or []
        task_type = str(task.get("type","general")).lower()
        impact_map = {"ubi":0.9,"wallet":0.7,"architecture":0.8,"meta":0.8,"voice":0.6}
        for tag in tags:
            t = str(tag).lower()
            if t in impact_map: impact = impact_map[t]; break
        if task_type in impact_map: impact = impact_map[task_type]
        revenue = max(0.0, (reward * urgency) / max(1.0, 1 + age_hours * 0.1))
        return PriorityComponents(impact=impact, revenue=revenue, risk=risk, latency=latency, trust=trust)

    async def canonical_score(self, task, twin_id, now_ts=None):
        w = await self.get_weights()
        p = self.build_p(task, twin_id, now_ts)
        score = max(0.0, _dot(w, p))
        meta = {"risk_budget": self.risk_budget(twin_id), "capital_assigned": self.capital_assigned(twin_id)}
        meta["capital_required"] = self.capital_required(task)
        meta["risk"] = round(p.risk, 4)
        if p.risk > meta["risk_budget"]: return 0.0, p, {**meta, "blocked": "risk_exceeded"}
        if meta["capital_assigned"] < meta["capital_required"]: return 0.0, p, {**meta, "blocked": "insufficient_capital"}
        return round(score, 4), p, meta

    def silence_rule_value_minus_cost(self, total_value, total_cost):
        return (total_value - total_cost) <= 0
