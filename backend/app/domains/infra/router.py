"""
Infra domain router.

Absorbs endpoints from:
  - routes/auth.py   (SIWE login/logout)
  - routes/api.py    (health, youtube skills, google sheets)
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

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
