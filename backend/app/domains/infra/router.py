"""
Infra domain router.

Absorbs endpoints from:
  - routes/auth.py   (SIWE login/logout)
  - routes/api.py    (health, youtube skills, google sheets)
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.domains.infra.deps import get_infra
from app.domains.infra.models import HealthResponse, SiweLoginRequest
from app.domains.infra.services import InfraServices

router = APIRouter(tags=["infra"])

InfraDep = Annotated[InfraServices, Depends(get_infra)]


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health")
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/status")
async def status() -> HealthResponse:
    return HealthResponse()


# ------------------------------------------------------------------
# SIWE Auth (from routes/auth.py)
# ------------------------------------------------------------------

@router.post("/auth/login")
async def siwe_login(
    payload: SiweLoginRequest,
    svc: InfraDep,
) -> dict[str, Any]:
    return await svc.verify_siwe(message=payload.message, signature=payload.signature)


@router.post("/auth/siwe")
async def siwe_login_legacy(
    payload: SiweLoginRequest,
    svc: InfraDep,
) -> dict[str, Any]:
    """Legacy path alias — identical to /auth/login."""
    return await svc.verify_siwe(message=payload.message, signature=payload.signature)


@router.post("/auth/logout")
async def siwe_logout() -> dict[str, Any]:
    return {"ok": True, "message": "logged out"}


# ------------------------------------------------------------------
# YouTube Skills (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/skills/youtube-search")
async def youtube_search(
    svc: InfraDep,
    q: str = "",
    limit: int = 8,
) -> dict[str, Any]:
    return await svc.youtube_search(q, limit=limit)


@router.post("/skills/learn-from-youtube")
async def learn_from_youtube(
    payload: dict[str, Any],
    svc: InfraDep,
) -> dict[str, Any]:
    video_id = payload.get("video_id", "")
    if not video_id:
        raise HTTPException(422, detail="video_id required")
    return await svc.youtube_learn(video_id)


# ------------------------------------------------------------------
# Google Sheets (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/google-sheets/read")
async def sheets_read(
    svc: InfraDep,
    spreadsheet_id: str = "",
    range: str = "",
) -> dict[str, Any]:
    return await svc.sheets_read(spreadsheet_id, range)


@router.post("/google-sheets/append")
async def sheets_append(
    payload: dict[str, Any],
    svc: InfraDep,
) -> dict[str, Any]:
    return await svc.sheets_append(
        payload["spreadsheet_id"],
        payload["range"],
        payload.get("values", []),
    )


# ------------------------------------------------------------------
# CLI Orchestration (from routes/cli.py)
# ------------------------------------------------------------------

@router.get("/cli/status")
async def cli_status(svc: InfraDep) -> dict[str, Any]:
    return svc.cli_status()


@router.post("/cli/enqueue")
async def cli_enqueue(payload: dict[str, Any], request: Request, svc: InfraDep) -> dict[str, Any]:
    cmd_id = (payload.get("cmd_id") or "").strip()
    args = payload.get("args") or []
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise HTTPException(400, detail="args must be a list[str]")
    created_by = request.headers.get("X-User-Id") or (request.client.host if request.client else "unknown")
    return await svc.cli_enqueue(cmd_id=cmd_id, args=args, created_by=created_by)


@router.get("/cli/queue/next")
async def cli_queue_next(svc: InfraDep, runner_id: str = "runner") -> dict[str, Any]:
    return await svc.cli_queue_next(runner_id=runner_id)


@router.post("/cli/report")
async def cli_report(payload: dict[str, Any], svc: InfraDep) -> dict[str, Any]:
    return await svc.cli_report(payload)


@router.get("/cli/history")
async def cli_history(svc: InfraDep, limit: int = 30) -> dict[str, Any]:
    return await svc.cli_history(limit=limit)
