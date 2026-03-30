"""
Infra domain router.

Absorbs endpoints from:
  - routes/auth.py   (SIWE login/logout)
  - routes/api.py    (health, youtube skills, google sheets)
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.domains.infra.deps import get_infra, require_jwt
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


@router.get("/auth/me")
async def auth_me(claims: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Return the authenticated identity from the JWT. Used by login.html to check existing sessions."""
    return {"sub": claims.get("sub"), "address": claims.get("sub"), "authority": claims.get("authority")}


@router.post("/auth/dev-login")
async def dev_login(payload: dict[str, Any]) -> dict[str, Any]:
    """Issue a JWT for a given address using BRIDGE_DEV_SECRET. Only available when ENV != production."""
    import os, hmac as _hmac
    if os.environ.get("ENV", "").lower() == "production":
        raise HTTPException(status_code=403, detail="Dev login disabled in production")
    dev_secret = os.environ.get("BRIDGE_DEV_SECRET", "")
    if not dev_secret:
        raise HTTPException(status_code=403, detail="BRIDGE_DEV_SECRET not configured")
    supplied = str(payload.get("secret", ""))
    if not _hmac.compare_digest(supplied, dev_secret):
        raise HTTPException(status_code=401, detail="Invalid dev secret")
    address = str(payload.get("address", "dev")).lower().strip()
    from app.services.siwe_auth import create_jwt
    token = create_jwt(address, authority="dev")
    return {"ok": True, "token": token, "address": address}


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


# ------------------------------------------------------------------
# Skills (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/skills")
async def list_skills(svc: InfraDep) -> dict[str, Any]:
    return await svc.list_skills()


@router.post("/skills")
async def add_skill(skill: dict[str, Any], svc: InfraDep) -> dict[str, Any]:
    return await svc.add_skill(skill)


# ------------------------------------------------------------------
# User settings (from routes/api.py)
# ------------------------------------------------------------------

def _uid_from_request(request: Request) -> str:
    uid = request.headers.get("X-User-Id") or request.headers.get("X-Bridge-User-Id")
    if uid and isinstance(uid, str) and uid.strip():
        return uid.strip()[:128]
    return "default"


@router.get("/user/settings")
async def get_user_settings(request: Request, svc: InfraDep) -> dict[str, Any]:
    return await svc.user_settings_get(_uid_from_request(request))


@router.put("/user/settings")
async def put_user_settings(request: Request, svc: InfraDep) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    uid = _uid_from_request(request)
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else (payload if isinstance(payload, dict) else {})
    return await svc.user_settings_put(uid, settings)


# ------------------------------------------------------------------
# Health extended (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/health/extended")
async def health_extended(svc: InfraDep) -> dict[str, Any]:
    return svc.health_extended()


# ------------------------------------------------------------------
# Sensors (from routes/api.py)
# ------------------------------------------------------------------

@router.post("/sensors/wifi")
async def sensors_wifi_post(payload: dict[str, Any], svc: InfraDep) -> dict[str, Any]:
    return await svc.sensors_wifi_post(payload)


@router.get("/sensors/wifi")
async def sensors_wifi_get(svc: InfraDep) -> dict[str, Any]:
    return await svc.sensors_wifi_get()


@router.post("/sensors/mouse")
async def sensors_mouse_post(payload: dict[str, Any], svc: InfraDep) -> dict[str, Any]:
    return await svc.sensors_mouse_post(payload)


@router.get("/sensors/mouse")
async def sensors_mouse_get(svc: InfraDep) -> dict[str, Any]:
    return await svc.sensors_mouse_get()


# ------------------------------------------------------------------
# Live map / report (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/live/map")
async def live_map(svc: InfraDep) -> dict[str, Any]:
    return await svc.live_map()


@router.get("/live/report")
async def live_report(svc: InfraDep) -> dict[str, Any]:
    from datetime import datetime
    data = await svc.live_map()
    data["report_at"] = datetime.utcnow().isoformat() + "Z"
    data["live_display"] = True
    return data


# ------------------------------------------------------------------
# Orchestrate + Wiki (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/orchestrate/directives")
async def orchestrate_directives(svc: InfraDep) -> dict[str, Any]:
    return svc.orchestrate_directives()


@router.get("/wiki/registry")
async def wiki_registry(svc: InfraDep) -> dict[str, Any]:
    return await svc.wiki_registry()


# ------------------------------------------------------------------
# KeyForge — Deterministic rotating key system
# ------------------------------------------------------------------

@router.get("/keyforge/status")
async def keyforge_status() -> dict[str, Any]:
    from app.services.keyforge import get_keyforge
    return get_keyforge().status()


@router.post("/keyforge/issue")
async def keyforge_issue(payload: dict[str, Any], _: dict = Depends(require_jwt)) -> dict[str, Any]:
    from app.services.keyforge import get_keyforge
    scope = payload.get("scope", "api-gateway")
    token = get_keyforge().issue(scope)
    return {"token": token, "scope": scope}


@router.post("/keyforge/validate")
async def keyforge_validate(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.keyforge import get_keyforge
    token = payload.get("token", "")
    if not token:
        raise HTTPException(400, detail="token required")
    result = get_keyforge().validate(token)
    return {"valid": result.valid, "scope": result.scope if result.valid else None}


@router.post("/keyforge/revoke")
async def keyforge_revoke(payload: dict[str, Any], _: dict = Depends(require_jwt)) -> dict[str, Any]:
    from app.services.keyforge import get_keyforge
    key_id = payload.get("key_id")
    scope = payload.get("scope")
    forge = get_keyforge()
    if key_id:
        forge.revoke_key(key_id)
    elif scope:
        forge.revoke_scope(scope)
    else:
        raise HTTPException(400, detail="key_id or scope required")
    return {"ok": True}
