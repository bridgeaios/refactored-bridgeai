"""Outreach queue service — email job management."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
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
        now = datetime.now(timezone.utc).isoformat()
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

    async def dispatch_pending(self, limit: int = 20) -> dict[str, Any]:
        """Fetch pending jobs, render templates, send via configured provider.
        Called by worker_loop every cycle. Returns summary dict."""
        from app.services.email_sender import send_email, PROVIDER
        from app.services.email_templates import render_template

        if not PROVIDER:
            return {"sent": 0, "failed": 0, "skipped": True, "reason": "no_provider"}

        ids: list = await self._mem.get("outreach:queue") or []
        sent = failed = 0
        for job_id in ids:
            if sent + failed >= limit:
                break
            job = await self._mem.get(f"outreach:job:{job_id}")
            if not job or job.get("status") != "pending":
                continue

            email = job.get("email", "")
            company = job.get("company", "")
            template_type = job.get("template_type", "general")

            # Use pre-rendered subject/body if set, otherwise render template
            subject = job.get("subject") or ""
            html_body = job.get("body") or ""
            if not subject or not html_body:
                subject, html_body, text_body = render_template(template_type, company, email)
            else:
                text_body = None

            result = await send_email(to=email, subject=subject, html=html_body, text=text_body)
            if result.get("ok"):
                await self.mark_sent(job_id)
                sent += 1
            else:
                error = result.get("error", "unknown")
                if not result.get("skipped"):
                    await self.mark_failed(job_id, error)
                    failed += 1

        log.info("[OUTREACH] dispatch: sent=%d failed=%d", sent, failed)
        return {"sent": sent, "failed": failed}

    async def mark_sent(self, job_id: str) -> dict[str, Any] | None:
        job = await self._mem.get(f"outreach:job:{job_id}")
        if not job:
            return None
        job["status"] = "sent"
        job["sent_at"] = datetime.now(timezone.utc).isoformat()
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
