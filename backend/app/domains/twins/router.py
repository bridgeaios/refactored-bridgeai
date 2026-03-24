"""
Twins domain router.
Absorbs twin/*, speech/*, emotion/*, bossbots/*, competition/* from routes/api.py.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

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
async def twin_shared_xml(svc: TwinsDep) -> dict[str, Any]:
    xml = await svc.shared_xml()
    return {"ok": True, "xml": xml}


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
