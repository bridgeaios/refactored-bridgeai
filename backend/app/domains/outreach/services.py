"""Outreach queue service — email job management."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore

log = logging.getLogger(__name__)

OUTREACH_STATUSES = ("pending", "sent", "failed", "bounced")


class OutreachService:
    """Email outreach queue backed by Redis/MemoryStore."""

    def __init__(self, memory: MemoryStore) -> None:
        self._mem = memory

    async def enqueue(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Queue an outreach email. Called by workers.py after lead ingestion."""
        job_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        job: dict[str, Any] = {
            "id": job_id,
            "email": payload.get("email", ""),
            "template_type": payload.get("template_type", "generic"),
            "company": payload.get("company", ""),
            "subject": payload.get("subject", ""),
            "body": payload.get("body", ""),
            "pain_points": payload.get("pain_points", []),
            "lead_id": payload.get("lead_id"),
            "status": "pending",
            "created_at": now,
            "sent_at": None,
            "error": None,
        }
        await self._mem.set(f"outreach:job:{job_id}", job)
        queue: list = await self._mem.get("outreach:queue") or []
        queue.append(job_id)
        await self._mem.set("outreach:queue", queue)
        log.info("Outreach job queued %s → %s", job_id, job["email"])
        return job

    async def list_queue(self, status: str | None = None) -> list[dict[str, Any]]:
        ids: list = await self._mem.get("outreach:queue") or []
        jobs = [await self._mem.get(f"outreach:job:{i}") for i in ids]
        jobs = [j for j in jobs if j]
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        return jobs

    async def mark_sent(self, job_id: str) -> dict[str, Any] | None:
        job = await self._mem.get(f"outreach:job:{job_id}")
        if not job:
            return None
        job["status"] = "sent"
        job["sent_at"] = datetime.utcnow().isoformat()
        await self._mem.set(f"outreach:job:{job_id}", job)
        return job

    async def mark_failed(self, job_id: str, error: str) -> dict[str, Any] | None:
        job = await self._mem.get(f"outreach:job:{job_id}")
        if not job:
            return None
        job["status"] = "failed"
        job["error"] = error[:500]
        await self._mem.set(f"outreach:job:{job_id}", job)
        return job

    async def history(self, limit: int = 50) -> list[dict[str, Any]]:
        ids: list = await self._mem.get("outreach:queue") or []
        jobs = [await self._mem.get(f"outreach:job:{i}") for i in ids]
        jobs = [j for j in jobs if j and j.get("status") != "pending"]
        jobs.sort(key=lambda x: x.get("sent_at") or x.get("created_at", ""), reverse=True)
        return jobs[:limit]

    async def stats(self) -> dict[str, Any]:
        ids: list = await self._mem.get("outreach:queue") or []
        jobs = [await self._mem.get(f"outreach:job:{i}") for i in ids]
        jobs = [j for j in jobs if j]
        by_status: dict[str, int] = {}
        for j in jobs:
            s = j.get("status", "pending")
            by_status[s] = by_status.get(s, 0) + 1
        return {"total": len(jobs), "by_status": by_status}
