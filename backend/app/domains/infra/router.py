"""
Infra domain router.

Absorbs endpoints from:
  - routes/auth.py   (SIWE login/logout)
  - routes/api.py    (health, youtube skills, google sheets)
"""
from __future__ import annotations

import time
from collections import deque
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response

from app.domains.infra.deps import get_infra, require_jwt
from app.domains.infra.models import HealthResponse, SiweLoginRequest
from app.domains.infra.services import InfraServices

router = APIRouter(tags=["infra"])

# Identity store key pattern: identity:link:{sub} → {contact_id, contact_email, ...}
_IDENTITY_KEY = "identity:link:{sub}"

InfraDep = Annotated[InfraServices, Depends(get_infra)]

# In-process ring buffer for SVG build + monetization telemetry (not durable across restarts).
_SVG_BUILD_TELEMETRY: deque[dict[str, Any]] = deque(maxlen=500)


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
# Telemetry (SVG build orchestration, monetization hooks)
# ------------------------------------------------------------------

@router.post("/telemetry")
async def post_api_telemetry(event: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Accept client/orchestrator events. Supports ``event`` or ``type`` = svg_build_completed."""
    etype = event.get("event") or event.get("type") or event.get("event_type")
    if etype == "svg_build_completed":
        _SVG_BUILD_TELEMETRY.append({**event, "received_at": time.time()})
    return {"ok": True, "accepted": True, "type": etype}


@router.get("/telemetry/svg-build")
async def get_svg_build_telemetry_recent(
    limit: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    """Recent ``svg_build_completed`` payloads (newest first). In-process buffer only; resets on restart."""
    items = list(_SVG_BUILD_TELEMETRY)
    tail = items[-limit:]
    tail.reverse()
    return {"ok": True, "items": tail, "count": len(tail)}


# ------------------------------------------------------------------
# SIWE Auth (from routes/auth.py)
# ------------------------------------------------------------------

@router.post("/auth/login")
async def siwe_login(
    payload: SiweLoginRequest,
    svc: InfraDep,
    response: Response,
) -> dict[str, Any]:
    """SIWE login: verifies wallet signature and sets HttpOnly cookie.
    Token is NOT returned in response body (XSS protection)."""
    result = await svc.verify_siwe(message=payload.message, signature=payload.signature)

    # Extract token and set as HttpOnly cookie
    token = result.get("token", "")
    if token:
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,          # Inaccessible to JavaScript
            secure=True,            # HTTPS only
            samesite="strict",      # CSRF protection
            path="/",
            max_age=24 * 60 * 60,   # 24 hours
        )

    # Return success WITHOUT token in body
    return {
        "ok": True,
        "address": result.get("address"),
        "message": "Authenticated. Token set as HttpOnly cookie."
    }


@router.post("/auth/siwe")
async def siwe_login_legacy(
    payload: SiweLoginRequest,
    svc: InfraDep,
    response: Response,
) -> dict[str, Any]:
    """Legacy path alias — identical to /auth/login. Sets HttpOnly cookie."""
    result = await svc.verify_siwe(message=payload.message, signature=payload.signature)

    # Extract token and set as HttpOnly cookie
    token = result.get("token", "")
    if token:
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            path="/",
            max_age=24 * 60 * 60,
        )

    return {
        "ok": True,
        "address": result.get("address"),
        "message": "Authenticated. Token set as HttpOnly cookie."
    }


@router.post("/auth/logout")
async def siwe_logout() -> dict[str, Any]:
    return {"ok": True, "message": "logged out"}


@router.get("/auth/me")
async def auth_me(claims: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Return the authenticated identity from the JWT, including linked CRM contact if any."""
    from app.core.deps import get_memory as _get_mem
    sub = claims.get("sub", "")
    mem = _get_mem()
    link = await mem.get(_IDENTITY_KEY.format(sub=sub)) or {}
    return {
        "sub": sub,
        "address": sub,
        "authority": claims.get("authority"),
        "contact_id": link.get("contact_id"),
        "contact_email": link.get("contact_email"),
        "contact_company": link.get("contact_company"),
        "linked": bool(link.get("contact_id")),
    }


@router.post("/identity/link-contact")
async def link_contact(
    payload: dict[str, Any],
    claims: dict = Depends(require_jwt),
) -> dict[str, Any]:
    """Link the authenticated user to a CRM contact by contact_id.
    This enables avatar and sub-services to inherit the contact's token context.
    """
    from app.core.deps import get_memory as _get_mem
    from app.domains.crm.services import CrmService
    from datetime import datetime, timezone

    contact_id = str(payload.get("contact_id", "")).strip()
    if not contact_id:
        raise HTTPException(400, detail="contact_id required")

    mem = _get_mem()
    crm = CrmService(memory=mem)
    contact = await crm.get_lead(contact_id)
    if not contact:
        raise HTTPException(404, detail="Contact not found")

    sub = claims.get("sub", "")
    link = {
        "sub": sub,
        "contact_id": contact_id,
        "contact_email": contact.get("email", ""),
        "contact_company": contact.get("company", ""),
        "contact_industry": contact.get("industry", ""),
        "contact_stage": contact.get("stage", "new"),
        "linked_at": datetime.now(timezone.utc).isoformat(),
        # Token context for avatar + sub-services
        "avatar_context": {
            "name": contact.get("name") or contact.get("email", ""),
            "company": contact.get("company", ""),
            "industry": contact.get("industry", ""),
            "score": contact.get("score", 0.0),
        },
    }
    await mem.set(_IDENTITY_KEY.format(sub=sub), link)

    # Also tag the CRM contact with the linked sub
    contact.setdefault("linked_subs", [])
    if sub not in contact["linked_subs"]:
        contact["linked_subs"].append(sub)
    await mem.set(f"crm:lead:{contact_id}", contact)

    return {"ok": True, "linked": True, "contact_id": contact_id, "avatar_context": link["avatar_context"]}


@router.get("/identity/me")
async def identity_me(
    claims: dict = Depends(require_jwt),
) -> dict[str, Any]:
    """Full identity context: JWT claims + linked contact + avatar/sub-service token context."""
    from app.core.deps import get_memory as _get_mem
    mem = _get_mem()
    sub = claims.get("sub", "")
    link = await mem.get(_IDENTITY_KEY.format(sub=sub)) or {}
    return {
        "sub": sub,
        "authority": claims.get("authority"),
        "linked": bool(link.get("contact_id")),
        "contact_id": link.get("contact_id"),
        "contact_email": link.get("contact_email"),
        "contact_company": link.get("contact_company"),
        "contact_industry": link.get("contact_industry"),
        "contact_stage": link.get("contact_stage"),
        "linked_at": link.get("linked_at"),
        "avatar_context": link.get("avatar_context", {}),
    }


@router.post("/identity/auto-link")
async def auto_link_by_email(
    payload: dict[str, Any],
    claims: dict = Depends(require_jwt),
) -> dict[str, Any]:
    """Auto-link authenticated user to a CRM contact matching by email address."""
    from app.core.deps import get_memory as _get_mem
    from app.domains.crm.services import CrmService
    from datetime import datetime, timezone

    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(400, detail="email required")

    mem = _get_mem()
    crm = CrmService(memory=mem)
    contact_id = await mem.get(f"crm:email:{email}")
    if not contact_id:
        # No existing contact — auto-ingest as new contact
        result = await crm.ingest_lead({
            "email": email,
            "name": payload.get("name", ""),
            "company": payload.get("company", ""),
            "source": "auth_auto_link",
            "osint_profile": {},
        })
        contact_id = result["id"]

    contact = await crm.get_lead(contact_id) or {}
    sub = claims.get("sub", "")
    link = {
        "sub": sub,
        "contact_id": contact_id,
        "contact_email": contact.get("email", email),
        "contact_company": contact.get("company", ""),
        "contact_industry": contact.get("industry", ""),
        "contact_stage": contact.get("stage", "new"),
        "linked_at": datetime.now(timezone.utc).isoformat(),
        "avatar_context": {
            "name": contact.get("name") or email,
            "company": contact.get("company", ""),
            "industry": contact.get("industry", ""),
            "score": contact.get("score", 0.0),
        },
    }
    await mem.set(_IDENTITY_KEY.format(sub=sub), link)

    contact.setdefault("linked_subs", [])
    if sub not in contact["linked_subs"]:
        contact["linked_subs"].append(sub)
    await mem.set(f"crm:lead:{contact_id}", contact)

    return {"ok": True, "contact_id": contact_id, "created": result.get("duplicate") is False if 'result' in dir() else False}


@router.post("/auth/dev-login")
async def dev_login(payload: dict[str, Any], response: Response) -> dict[str, Any]:
    """Issue a JWT for a given address using BRIDGE_DEV_SECRET. Only available when ENV != production.
    Sets HttpOnly cookie (token NOT returned in body)."""
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

    is_secure = os.environ.get("ENV", "").lower() == "production"
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/",
        max_age=24 * 60 * 60,
    )

    # Also return token in body so the frontend can store it in localStorage
    # for Authorization: Bearer header auth (used by dashboard pages)
    return {"ok": True, "address": address, "token": token, "message": "Dev login successful."}


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
    from datetime import datetime, timezone
    data = await svc.live_map()
    data["report_at"] = datetime.now(timezone.utc).isoformat() + "Z"
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
