# ruff: noqa: B008
"""
Infra domain: health, training, eSIM, SIWE auth, system comprehension, TTS, founder todo.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.cortex import (
    auth_class_from_token,
    authority_allows,
    capability_enabled,
    wrap_response,
)
from app.domains.infra.deps import get_infra
from app.domains.infra.models import HealthResponse, SiweLoginRequest
from app.domains.infra.services import InfraServices
from app.physics import (
    DRIFT_THRESHOLD,
    consume_evolution_budget,
    drift_score,
    replenish_evolution_budget,
    should_trigger_governance,
)
from app.runtime import (
    emotion_service,
    esim_service,
    learning_service,
    mission_service,
    system_comprehension,
    voice_broker,
)
from app.services.system_comprehension import SKILL_DEFINITION as SYS_COMP_SKILL_DEF

router = APIRouter(tags=["infra"])

FOUNDER_TODO_PATH = (
    Path(os.environ.get("BRIDGE_LIVE_WALL_PATH", "C:/Users/supas/BridgeLiveWall"))
    / "founder-todo.json"
)


def _read_founder_todo() -> dict:
    if not FOUNDER_TODO_PATH.exists():
        return {"version": 1, "updatedAt": None, "objectives": []}
    with open(FOUNDER_TODO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_founder_todo(data: dict) -> None:
    FOUNDER_TODO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FOUNDER_TODO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True}


@router.get("/health/extended")
async def health_extended() -> dict[str, Any]:
    from app.physics import (
        economic_circuit_breaker_tripped,
        economic_entropy_score,
        telemetry,
    )

    err_rate = 0.0
    total = telemetry.state_mutation_count + telemetry.failed_mutation_count
    if total > 0:
        err_rate = telemetry.failed_mutation_count / total
    silence_dev = abs(telemetry.silence_rate - 0.5) * 2
    dl = list(telemetry.decision_latency_ms)
    p95 = sorted(dl)[int(len(dl) * 0.95)] if dl else 0
    latency_factor = 1.0 if p95 <= 100 else max(0, 1.0 - (p95 - 100) / 500)
    circuit_ok = 0.0 if economic_circuit_breaker_tripped() else 1.0
    entropy_ok = 1.0 - min(1.0, economic_entropy_score())
    health_score = (1 - err_rate) * (1 - silence_dev) * latency_factor * circuit_ok * entropy_ok
    return {
        "ok": health_score >= 0.5,
        "health_score": round(health_score, 4),
        "components": {
            "error_rate": round(err_rate, 4),
            "silence_spike_deviation": round(silence_dev, 4),
            "latency_factor": round(latency_factor, 4),
            "circuit_breaker_ok": circuit_ok,
            "entropy_ok": round(entropy_ok, 4),
        },
    }


@router.get("/status")
async def status() -> HealthResponse:
    return HealthResponse()


@router.post("/auth/siwe")
async def auth_siwe(req: dict, svc: InfraServices = Depends(get_infra)) -> dict[str, Any]:
    """Legacy SIWE body: {message, signature}."""
    message = (req.get("message") or "").strip()
    signature = (req.get("signature") or "").strip()
    return await svc.verify_siwe(message=message, signature=signature, address=None)


@router.post("/auth/login")
async def auth_login(
    payload: SiweLoginRequest,
    svc: InfraServices = Depends(get_infra),
) -> dict[str, Any]:
    return await svc.verify_siwe(
        message=payload.message,
        signature=payload.signature,
        address=payload.address,
    )


@router.post("/auth/logout")
async def auth_logout() -> dict[str, Any]:
    return {"ok": True, "message": "logged out"}


@router.get("/skills/youtube-search")
async def youtube_search(
    q: str,
    limit: int = 8,
    svc: InfraServices = Depends(get_infra),
) -> dict[str, Any]:
    return await svc.youtube_search(q, limit=limit)


@router.post("/skills/learn-from-youtube")
async def learn_from_youtube(
    payload: dict[str, Any],
    svc: InfraServices = Depends(get_infra),
) -> dict[str, Any]:
    video_id = payload.get("video_id", "")
    if not video_id:
        raise HTTPException(422, detail="video_id required")
    return await svc.youtube_learn(video_id)


@router.get("/google-sheets/read")
async def sheets_read(
    spreadsheet_id: str,
    range: str,
    svc: InfraServices = Depends(get_infra),
) -> dict[str, Any]:
    return await svc.sheets_read(spreadsheet_id, range)


@router.post("/google-sheets/append")
async def sheets_append(
    payload: dict[str, Any],
    svc: InfraServices = Depends(get_infra),
) -> dict[str, Any]:
    return await svc.sheets_append(
        payload["spreadsheet_id"],
        payload["range"],
        payload.get("values", []),
    )


@router.post("/train/start")
async def train_start() -> dict[str, Any]:
    started = await learning_service.train(emotion_service)
    if started:
        replenish_evolution_budget(2.0, "training_completion")
    return {"started": bool(started)}


@router.get("/train/status")
async def train_status() -> dict[str, Any]:
    return learning_service.get_status()


@router.get("/esim/status")
async def esim_status() -> dict[str, Any]:
    return esim_service.get_status()


@router.get("/system/comprehension")
async def system_comprehension_map() -> dict[str, Any]:
    return system_comprehension.get_system_map()


@router.get("/system/comprehension/explain")
async def system_comprehension_explain(level: int = 1) -> dict[str, Any]:
    return {"level": level, "explanation": system_comprehension.explain(level)}


@router.get("/system/comprehension/operational-model")
async def system_comprehension_operational() -> dict[str, Any]:
    return {"model": system_comprehension.get_operational_model()}


@router.get("/system/comprehension/role-awareness")
async def system_comprehension_roles() -> dict[str, Any]:
    return system_comprehension.get_role_awareness()


@router.post("/system/comprehension/check-alignment")
async def system_comprehension_check_alignment(payload: dict) -> dict[str, Any]:
    action = payload.get("action") or ""
    context = payload.get("context") or {}
    result = system_comprehension.check_alignment(action, context)
    return {
        "aligned": result.aligned,
        "reason": result.reason,
        "confidence": result.confidence,
        "clarification_needed": result.clarification_needed,
    }


@router.post("/system/comprehension/evolve")
async def system_comprehension_evolve(payload: dict) -> dict[str, Any]:
    if not capability_enabled("evolution"):
        return wrap_response({"error": "evolution disabled"}, ok=False, silence=True)
    auth = auth_class_from_token(payload.get("authToken"))
    if not authority_allows(auth, "evolution"):
        return wrap_response({"error": "orchestrator authority required"}, ok=False, silence=True)
    if not consume_evolution_budget():
        return wrap_response({"error": "evolution_budget_exhausted"}, ok=False, silence=True)
    return system_comprehension.evolve(payload)


@router.get("/system/comprehension/skill")
async def system_comprehension_skill() -> dict[str, Any]:
    return SYS_COMP_SKILL_DEF


@router.get("/audit/drift")
async def audit_drift() -> dict[str, Any]:
    board = await mission_service.get_counts()
    current_state = {"mission_board": board}
    drift = drift_score(current_state)
    trigger = should_trigger_governance(drift)
    return {
        "drift_score": round(drift, 4),
        "threshold": DRIFT_THRESHOLD,
        "should_trigger_governance": trigger,
        "mission_board": board,
    }


@router.get("/tts/available")
async def tts_available() -> dict[str, bool]:
    try:
        return {"available": True}
    except Exception:
        return {"available": False}


@router.post("/tts")
async def text_to_speech(payload: dict) -> Response:
    text = payload.get("text") or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="text required")
    voice_id = payload.get("voice_id") or "21m00Tcm4TlvDq8ikWAM"
    try:
        chunks = []
        async for chunk in voice_broker.stream_tts(text[:1000], voice_id):
            chunks.append(chunk)
        return Response(
            b"".join(chunks),
            media_type="audio/mpeg",
            headers={"X-Deprecation": "Prefer /api/speech/embody/speak for phoneme-aware use"},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/founder-todo")
async def get_founder_todo() -> dict[str, Any]:
    return _read_founder_todo()


@router.patch("/founder-todo/{obj_id}/complete")
async def complete_founder_objective(obj_id: str) -> dict[str, Any]:
    data = _read_founder_todo()
    objs = data.get("objectives", [])
    found = False
    for o in objs:
        if o.get("id") == obj_id:
            o["status"] = "complete"
            o["completedAt"] = datetime.utcnow().isoformat() + "Z"
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail=f"Objective '{obj_id}' not found")
    data["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    _write_founder_todo(data)
    return {"ok": True, "id": obj_id, "status": "complete"}
