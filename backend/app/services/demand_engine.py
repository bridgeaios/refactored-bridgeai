"""
Demand Engine — continuously feeds the marketplace so agents don't idle.

This is a first-pass, minimal "pump" implementation:
- it generates useful task templates (marketing automation / scraping / analytics)
- it respects a target backlog (won't overfill)
- it is safe to call repeatedly (idempotent-ish via content hashing)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from app.services.priority_routing import compute_priority_score, passes_threshold, TARGET_PRIORITY


DEFAULT_TASK_TEMPLATES: list[dict] = [
    {
        "type": "marketing",
        "title": "Generate 5 ad angles for a client offer",
        "description": "Draft 5 high-converting ad angles + 3 headlines each.",
        "reward": 3.0,
        "urgency": 0.9,
        "tags": ["marketing", "copy"],
    },
    {
        "type": "leadgen",
        "title": "Extract 100 leads from a directory page",
        "description": "Parse names, emails, phone, and website into a CSV.",
        "reward": 5.0,
        "urgency": 1.0,
        "tags": ["leadgen", "extraction"],
    },
    {
        "type": "analytics",
        "title": "Summarize weekly funnel performance",
        "description": "Compute CTR/CVR, identify biggest drop-offs, propose 3 fixes.",
        "reward": 4.0,
        "urgency": 0.95,
        "tags": ["analytics", "reporting"],
    },
    {
        "type": "automation",
        "title": "Create a Zapier-style workflow spec",
        "description": "Define triggers/actions + edge cases for a SaaS automation.",
        "reward": 3.5,
        "urgency": 0.85,
        "tags": ["automation", "workflows"],
    },
]


def _task_fingerprint(task: dict) -> str:
    base = f'{task.get("type","")}::{task.get("title","")}::{task.get("description","")}::{task.get("reward","")}'
    return hashlib.sha256(base.encode("utf-8", errors="ignore")).hexdigest()[:16]


@dataclass
class DemandPumpResult:
    created: int
    skipped: int
    open_tasks: int
    target_backlog: int


class DemandEngineService:
    def __init__(self, marketplace):
        self.marketplace = marketplace
        self._seen: set[str] = set()

    def pump(
        self,
        *,
        target_backlog: int = 50,
        max_create: int = 25,
        templates: list[dict] | None = None,
        source: str = "demand-engine",
    ) -> DemandPumpResult:
        """
        Priority-aware: if avg_priority < TARGET_PRIORITY, create high-value tasks; else throttle.
        """
        now = time.time()
        templates = templates or DEFAULT_TASK_TEMPLATES
        open_tasks = self.marketplace.get_open_count()
        ordered = self.marketplace.get_tasks(twin_id="system", status="open")
        scores = [float(t.get("_priority_score", 0)) for t in ordered if t.get("_priority_score") is not None]
        avg_priority = sum(scores) / len(scores) if scores else 0

        need = max(0, int(target_backlog) - int(open_tasks))
        to_create = min(int(max_create), need)
        if avg_priority >= TARGET_PRIORITY and open_tasks >= target_backlog // 2:
            to_create = min(to_create, 2)
        created = 0
        skipped = 0

        templates_sorted = sorted(templates, key=lambda x: float(x.get("reward", 0) or 0), reverse=True)
        i = 0
        while created < to_create and i < (to_create * 3):
            t = templates_sorted[i % len(templates_sorted)].copy()
            fp = _task_fingerprint(t)
            if fp in self._seen:
                skipped += 1
                i += 1
                continue
            self._seen.add(fp)
            task_payload = {
                "title": t.get("title"),
                "desc": t.get("title") or t.get("desc"),
                "description": t.get("description"),
                "reward": float(t.get("reward", 0) or 0),
                "urgency": float(t.get("urgency", 1.0) or 1.0),
                "tags": t.get("tags", []),
                "type": t.get("type", "general"),
                "source": source,
                "created_at": now,
                "fingerprint": fp,
            }
            score, _ = compute_priority_score(task_payload, trust=0.5, now_ts=now)
            if passes_threshold(score):
                self.marketplace.add_task(task_payload)
                created += 1
            i += 1

        open_tasks_after = self.marketplace.get_open_count()
        return DemandPumpResult(
            created=created,
            skipped=skipped,
            open_tasks=open_tasks_after,
            target_backlog=int(target_backlog),
        )

