"""Outreach domain router — email queue management."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.domains.outreach.deps import get_outreach
from app.domains.outreach.services import OutreachService
from app.domains.infra.deps import require_jwt

router = APIRouter(tags=["outreach"])

OutreachDep = Annotated[OutreachService, Depends(get_outreach)]


@router.post("/outreach/queue")
async def enqueue(
    payload: dict[str, Any],
    svc: OutreachDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    """Called by workers.py after lead ingestion. Accepts email job payload."""
    job = await svc.enqueue(payload)
    return {"ok": True, "job": job}


@router.get("/outreach/queue")
async def list_queue(
    svc: OutreachDep,
    _: dict = Depends(require_jwt),
    status: str | None = None,
) -> dict[str, Any]:
    jobs = await svc.list_queue(status=status)
    return {"ok": True, "jobs": jobs, "count": len(jobs)}


@router.post("/outreach/jobs/{job_id}/sent")
async def mark_sent(job_id: str, svc: OutreachDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    job = await svc.mark_sent(job_id)
    if not job:
        raise HTTPException(404, detail="Job not found")
    return {"ok": True, "job": job}


@router.post("/outreach/jobs/{job_id}/failed")
async def mark_failed(
    job_id: str,
    payload: dict[str, Any],
    svc: OutreachDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    job = await svc.mark_failed(job_id, payload.get("error", ""))
    if not job:
        raise HTTPException(404, detail="Job not found")
    return {"ok": True, "job": job}


@router.get("/outreach/history")
async def history(
    svc: OutreachDep,
    _: dict = Depends(require_jwt),
    limit: int = 50,
) -> dict[str, Any]:
    jobs = await svc.history(limit=limit)
    return {"ok": True, "jobs": jobs, "count": len(jobs)}


@router.get("/outreach/stats")
async def stats(svc: OutreachDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    return await svc.stats()
