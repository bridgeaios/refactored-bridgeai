"""
Twins domain router.
Absorbs twin/*, speech/*, emotion/*, bossbots/*, competition/* from routes/api.py.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.domains.twins.deps import get_twins
from app.domains.twins.models import (
    CompetitionSubmitRequest,
    DecideRequest,
    EmotionUpdateRequest,
    SpeakRequest,
)
from app.domains.twins.services import TwinsServices

router = APIRouter(tags=["twins"])

TwinsDep = Annotated[TwinsServices, Depends(get_twins)]


@router.get("/twin/profile")
async def twin_profile(
    svc: TwinsDep,
    twin_id: str = "default",
) -> dict[str, Any]:
    return svc.get_profile(twin_id)


@router.post("/twin/decide")
async def twin_decide(
    payload: DecideRequest,
    svc: TwinsDep,
) -> dict[str, Any]:
    return await svc.decide(prompt=payload.prompt, twin_id=payload.twin_id, context=payload.context)


@router.get("/twin/shared-xml")
async def twin_shared_xml(svc: TwinsDep) -> Any:
    from fastapi.responses import Response
    xml = await svc.shared_xml()
    return Response(content=xml, media_type="application/xml")


@router.post("/twin/shared-xml")
async def set_shared_xml(request: Request, svc: TwinsDep) -> dict[str, Any]:
    body_bytes = await request.body()
    xml = body_bytes.decode("utf-8", errors="replace").strip()
    return await svc.set_shared_xml(xml)


@router.get("/emotion/status")
async def emotion_status(
    svc: TwinsDep,
    twin_id: str = "default",
) -> dict[str, Any]:
    return await svc.emotion_status(twin_id)


@router.post("/emotion/update")
async def emotion_update(
    payload: EmotionUpdateRequest,
    svc: TwinsDep,
) -> dict[str, Any]:
    return await svc.emotion_update(
        twin_id=payload.twin_id,
        emotion=payload.emotion,
        intensity=payload.intensity,
    )


@router.post("/speech/speak")
async def speech_speak(
    payload: SpeakRequest,
    svc: TwinsDep,
) -> dict[str, Any]:
    return await svc.speak(text=payload.text, twin_id=payload.twin_id, voice=payload.voice)


@router.get("/competition/status")
async def competition_status(svc: TwinsDep) -> dict[str, Any]:
    return await svc.competition_status()


@router.post("/competition/submit")
async def competition_submit(
    payload: CompetitionSubmitRequest,
    svc: TwinsDep,
) -> dict[str, Any]:
    return await svc.competition_submit(
        twin_id=payload.twin_id,
        round_id=payload.round_id,
        answer=payload.answer,
    )


@router.get("/bossbots")
async def list_bossbots(svc: TwinsDep) -> dict[str, Any]:
    bots = svc.list_bossbots()
    return {"ok": True, "bossbots": bots}


# ------------------------------------------------------------------
# BossBots extended (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/bossbots/signals")
async def bossbots_signals(svc: TwinsDep) -> Any:
    return svc.bossbots_signals()


@router.post("/bossbots/trade")
async def bossbots_trade(trade: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    asset = trade.get("asset") if isinstance(trade, dict) else None
    if not asset:
        raise HTTPException(400, detail="asset required")
    twin_id = trade.get("twin_id", "system")
    return svc.bossbots_trade(asset=str(asset), twin_id=str(twin_id))


# ------------------------------------------------------------------
# Twins competition extended (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/twins")
async def list_twins(svc: TwinsDep) -> Any:
    return svc.list_twins()


@router.get("/twins/leaderboard")
async def twins_leaderboard(svc: TwinsDep) -> Any:
    return svc.twins_leaderboard()


@router.post("/twins/auto-add")
async def twins_auto_add(svc: TwinsDep) -> dict[str, Any]:
    return svc.twins_auto_add()


@router.post("/twins/allocate")
async def twins_allocate(data: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    task_id = data.get("task_id")
    twin_id = data.get("twin_id")
    if not task_id or not twin_id:
        raise HTTPException(400, detail="task_id and twin_id required")
    return svc.twins_allocate(task_id=int(task_id), twin_id=str(twin_id))


@router.post("/twins/teach")
async def twins_teach(data: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    teacher_id = data.get("teacher_id")
    student_id = data.get("student_id")
    skill_name = data.get("skill_name")
    if not teacher_id or not student_id or not skill_name:
        raise HTTPException(400, detail="teacher_id, student_id, and skill_name required")
    return svc.twins_teach(teacher_id=str(teacher_id), student_id=str(student_id), skill_name=str(skill_name))


# ------------------------------------------------------------------
# Twin sim / evolve / env-keys (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/twin/env-keys")
async def twin_env_keys(svc: TwinsDep) -> dict[str, Any]:
    return svc.env_keys()


@router.post("/twin/simulate")
async def twin_simulate(payload: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    return svc.simulate(payload)


@router.post("/twin/evolve")
async def twin_evolve(payload: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    return svc.evolve(payload)


# ------------------------------------------------------------------
# Emotion compute (from routes/api.py)
# ------------------------------------------------------------------

@router.post("/emotion/compute")
async def emotion_compute(payload: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    return await svc.emotion_compute(payload)


# ------------------------------------------------------------------
# Training + eSIM (from routes/api.py)
# ------------------------------------------------------------------

@router.post("/train/start")
async def train_start(svc: TwinsDep) -> dict[str, Any]:
    return await svc.train_start()


@router.get("/train/status")
async def train_status(svc: TwinsDep) -> dict[str, Any]:
    return svc.train_status()


@router.get("/esim/status")
async def esim_status(svc: TwinsDep) -> dict[str, Any]:
    return svc.esim_status()


# ------------------------------------------------------------------
# Speech embodiment (from routes/api.py)
# ------------------------------------------------------------------

@router.post("/speech/embody")
async def speech_embody(payload: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    transcript = payload.get("transcript") or payload.get("prompt") or payload.get("text") or ""
    context = payload.get("context") or {}
    audience = payload.get("audience_model") or {}
    return await svc.speech_embody(transcript=transcript, context=context, audience_model=audience)


@router.post("/speech/embody/speak")
async def speech_embody_speak(payload: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    text = payload.get("text") or ""
    return await svc.speech_embody_speak(text=text)


@router.get("/speech/embodiment/skill")
async def speech_embodiment_skill(svc: TwinsDep) -> dict[str, Any]:
    return svc.speech_embodiment_skill()


@router.post("/speech/embodiment/memory/clear")
async def speech_embodiment_memory_clear(svc: TwinsDep) -> dict[str, Any]:
    return svc.speech_embodiment_memory_clear()


@router.get("/speech/embodiment/memory")
async def speech_embodiment_memory(svc: TwinsDep) -> dict[str, Any]:
    return svc.speech_embodiment_memory()


@router.post("/speech/reason")
async def speech_reason(payload: dict[str, Any], svc: TwinsDep) -> dict[str, Any]:
    transcript = payload.get("transcript") or payload.get("text") or ""
    context = payload.get("context") or {}
    return await svc.speech_reason(prompt=transcript, context=context)


# ------------------------------------------------------------------
# State mutation (from BRIDGE_AI_OS main.py POST /api/state)
# ------------------------------------------------------------------

@router.post("/state")
async def state_mutation(body: dict[str, Any]) -> dict[str, Any]:
    """Request state change via reducer. Dispatches through the reducer registry."""
    from app.reducers import SANCTIONED_NAMES, STRICT_MODE
    reducer = body.get("reducer")
    payload = body.get("payload") or {}
    if not reducer or not isinstance(reducer, str):
        raise HTTPException(400, detail="reducer required")
    if STRICT_MODE and reducer not in SANCTIONED_NAMES:
        raise HTTPException(403, detail=f"reducer '{reducer}' not sanctioned")
    # In Site B the reducers are dispatched via the physics/cortex layer.
    # Publish the reducer event for any listeners.
    try:
        from app.physics import emit as physics_emit
        await physics_emit("reducer", {"reducer": reducer, "payload": payload})
    except Exception:
        pass
    return {"ok": True, "reducer": reducer}
