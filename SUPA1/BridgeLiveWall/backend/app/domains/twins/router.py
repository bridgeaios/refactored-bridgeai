# ruff: noqa: B008
"""
Twins domain: cognitive twin, emotion, speech embodiment, twins competition.
"""
from __future__ import annotations

import base64
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from app.cortex import (
    auth_class_from_token,
    authority_allows,
    capability_enabled,
    get_state_version,
    wrap_response,
)
from app.domains.twins.deps import get_twins
from app.domains.twins.models import CompetitionSubmitRequest, EmotionUpdateRequest, SpeakRequest
from app.domains.twins.services import TwinsServices
from app.physics import (
    DETERMINISTIC_MODE,
    consume_evolution_budget,
    deterministic_seed,
    ethical_conflict_score,
    ethical_reason_category,
    fallback_for,
    get_degradation,
    replenish_evolution_budget,
    should_silence_for_ethics,
    telemetry,
    validate_identity_immutability,
)
from app.runtime import (
    cognitive_twin,
    emotion_service,
    marketplace_service,
    memory,
    speech_embodiment,
    speech_reasoning,
    system_comprehension,
    twins_competition,
    voice_broker,
)
from app.services.speech_embodiment import SKILL_DEFINITION

router = APIRouter(tags=["twins"])

TWIN_XML_KEY = "twin:shared_xml"
DEFAULT_TWIN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<twin>
  <authority>I am the Bridge. I am the Founder. I am the System. I am the Authority.</authority>
  <backend>human</backend>
  <mission><backlog>0</backlog><in_progress>0</in_progress><review>0</review><done>0</done></mission>
  <face_state>ALIVE</face_state>
</twin>"""


@router.get("/twin/shared-xml", response_class=PlainTextResponse)
async def get_shared_xml() -> Response:
    xml = await memory.get(TWIN_XML_KEY)
    if xml is None:
        xml = DEFAULT_TWIN_XML
        await memory.set(TWIN_XML_KEY, xml)
    return Response(content=xml, media_type="application/xml")


@router.post("/twin/shared-xml")
async def set_shared_xml(request: Request) -> dict[str, Any]:
    body_bytes = await request.body()
    xml = body_bytes.decode("utf-8", errors="replace").strip()
    if not xml or not xml.lstrip().startswith("<"):
        raise HTTPException(status_code=400, detail="valid XML required")
    await memory.set(TWIN_XML_KEY, xml)
    return {"ok": True}


@router.get("/twin/profile")
async def get_twin_profile(
    twin_id: str = "default",
    svc: TwinsServices = Depends(get_twins),
) -> dict[str, Any]:
    return svc.get_profile(twin_id)


@router.post("/twin/decide")
async def twin_decide(payload: dict) -> dict[str, Any]:
    t0 = time.perf_counter()
    env = payload.get("environment", {})
    if payload.get("prompt") and not env:
        env = {"prompt": payload.get("prompt")}
    goal = payload.get("goal_vector", [])
    constraints = set(payload.get("constraints", []))
    risk = float(payload.get("risk_threshold", 0.5))
    candidates = payload.get("candidates", [])
    state_version = await get_state_version(memory)
    seed = deterministic_seed({"env": env, "goal": goal, "candidates": candidates}, state_version)
    if DETERMINISTIC_MODE:
        import random

        random.seed(seed)
    result = cognitive_twin.decide(env, goal, constraints, risk, candidates)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    telemetry.record_decision(elapsed_ms)
    if DETERMINISTIC_MODE:
        telemetry.record_decision_with_seed(seed, state_version)
    if result is None:
        telemetry.record_silence()
        return wrap_response(
            {"action": None, "reason": "no_positive_value_output"},
            silence=True,
            confidence=0.0,
            deterministic_seed=seed,
            state_version=state_version,
        )
    action = result.get("action", {})
    action_obj = action if isinstance(action, dict) else {"action": action}
    ethical_score = ethical_conflict_score(action_obj, {"environment": env})
    if should_silence_for_ethics(action_obj, {"environment": env}):
        telemetry.record_silence()
        return wrap_response(
            {"action": None, "reason": "ethical_conflict"},
            silence=True,
            confidence=0.0,
            deterministic_seed=seed,
            state_version=state_version,
            ethical_score=ethical_score,
            ethical_reason=ethical_reason_category(action_obj, {"environment": env}),
        )
    action_id = (
        (action_obj.get("action_id") or action_obj.get("action") or "")
        if isinstance(action_obj, dict)
        else str(action_obj)
    )
    if action_id:
        aligned, reason = system_comprehension.filter_action(action_id, {"environment": env})
        if not aligned:
            telemetry.record_silence()
            return wrap_response(
                {"action": None, "reason": f"alignment_filter:{reason}"},
                silence=True,
                confidence=0.0,
                deterministic_seed=seed,
                state_version=state_version,
                ethical_reason="alignment_filter",
            )
    telemetry.record_action()
    return wrap_response(
        result,
        silence=False,
        confidence=result.get("confidence", 0.8),
        deterministic_seed=seed,
        state_version=state_version,
    )


@router.post("/twin/simulate")
async def twin_simulate(payload: dict) -> dict[str, Any]:
    twin_id = payload.get("twin_id", "default")
    deg = get_degradation(twin_id)
    uncertainty = payload.get("uncertainty", 0)
    pressure = payload.get("pressure", 0)
    deg.accumulate_stress(uncertainty * 0.1)
    deg.set_cognitive_load(pressure)
    deg.decay_under_pressure(pressure)
    result = cognitive_twin.simulate_behavior(payload)
    result["simulation"] = True
    result["committed"] = False
    result["performance_factor"] = deg.performance_factor
    return result


@router.post("/twin/evolve")
async def twin_evolve(payload: dict) -> dict[str, Any]:
    if not capability_enabled("evolution"):
        return wrap_response(
            {"error": "evolution disabled", "feedback_ingested": False},
            ok=False,
            silence=True,
        )
    auth = auth_class_from_token(payload.get("authToken"))
    if not authority_allows(auth, "evolution"):
        return wrap_response(
            {"error": "orchestrator authority required", "feedback_ingested": False},
            ok=False,
            silence=True,
        )
    if not consume_evolution_budget():
        return wrap_response(
            {"error": "evolution_budget_exhausted", "feedback_ingested": False},
            ok=False,
            silence=True,
        )
    valid, reason = validate_identity_immutability(payload)
    if not valid:
        replenish_evolution_budget(1.0, "rollback_identity")
        telemetry.record_failed_mutation()
        return wrap_response(
            {"error": reason, "feedback_ingested": False},
            ok=False,
            silence=True,
        )
    evolution_mode = payload.get("evolution_mode", "sandbox")
    result = cognitive_twin.evolve(payload)
    result["evolution_mode"] = evolution_mode
    result["committed"] = False
    return result


@router.post("/emotion/compute")
async def compute_emotion(payload: dict) -> dict[str, Any]:
    try:
        return await emotion_service.compute(payload)
    except Exception:
        return fallback_for("emotion")


@router.get("/emotion/status")
async def emotion_status(
    twin_id: str = "default",
    svc: TwinsServices = Depends(get_twins),
) -> dict[str, Any]:
    return await svc.emotion_status(twin_id)


@router.post("/emotion/update")
async def emotion_update(
    payload: EmotionUpdateRequest,
    svc: TwinsServices = Depends(get_twins),
) -> dict[str, Any]:
    return await svc.emotion_update(
        twin_id=payload.twin_id,
        emotion=payload.emotion,
        intensity=payload.intensity,
    )


@router.post("/speech/reason")
async def speech_reason(payload: dict) -> dict[str, Any]:
    transcript = payload.get("transcript") or payload.get("text") or ""
    context = payload.get("context") or {}
    result = speech_reasoning.process(transcript, context=context)
    return speech_reasoning.to_dict(result)


@router.post("/speech/speak")
async def speech_speak(
    payload: SpeakRequest,
    svc: TwinsServices = Depends(get_twins),
) -> dict[str, Any]:
    return await svc.speak(text=payload.text, twin_id=payload.twin_id, voice=payload.voice)


@router.post("/speech/embody")
async def speech_embody(payload: dict) -> dict[str, Any]:
    transcript = payload.get("transcript") or payload.get("prompt") or payload.get("text") or ""
    context = payload.get("context") or {}
    audience = payload.get("audience_model") or {}
    embody, execution_plan = speech_embodiment.process(
        transcript,
        context=context,
        audience_model=audience,
    )
    if embody.silence:
        return {
            "response": "",
            "phonemes": [],
            "emotion": embody.emotion,
            "prosody": {
                "pitch": embody.prosody.pitch,
                "tempo": embody.prosody.tempo,
                "intensity": embody.prosody.intensity,
            },
            "audio_base64": None,
            "silence": True,
            "confidence": embody.confidence,
            "execution_plan": execution_plan,
        }
    t0 = time.perf_counter()
    audio_b64 = None
    try:
        chunks = []
        async for chunk in voice_broker.stream_tts(embody.text[:1000]):
            chunks.append(chunk)
        audio_b64 = base64.b64encode(b"".join(chunks)).decode("ascii")
    except RuntimeError:
        pass
    telemetry.record_speech((time.perf_counter() - t0) * 1000)
    phoneme_list = [
        {"viseme": p.viseme, "start_ms": p.start_ms, "end_ms": p.end_ms}
        for p in embody.phonemes
    ]
    return {
        "response": embody.text,
        "phonemes": phoneme_list,
        "emotion": embody.emotion,
        "prosody": {
            "pitch": embody.prosody.pitch,
            "tempo": embody.prosody.tempo,
            "intensity": embody.prosody.intensity,
        },
        "audio_base64": audio_b64,
        "silence": False,
        "confidence": embody.confidence,
        "execution_plan": execution_plan,
        "viseme_map": {
            v: speech_embodiment.viseme_to_expression(v)
            for v in ("AA", "EE", "OH", "FV", "BMP", "TH", "Rest")
        },
    }


@router.post("/speech/embody/speak")
async def speech_embody_speak(payload: dict) -> dict[str, Any]:
    text = payload.get("text") or ""
    if not text.strip():
        return {"response": "", "phonemes": [], "audio_base64": None, "viseme_map": {}}
    phonemes = speech_embodiment.text_to_phoneme_sequence(text)
    phoneme_list = [
        {"viseme": p.viseme, "start_ms": p.start_ms, "end_ms": p.end_ms}
        for p in phonemes
    ]
    audio_b64 = None
    try:
        chunks = []
        async for chunk in voice_broker.stream_tts(text[:1000]):
            chunks.append(chunk)
        audio_b64 = base64.b64encode(b"".join(chunks)).decode("ascii")
    except RuntimeError:
        pass
    return {
        "response": text,
        "phonemes": phoneme_list,
        "emotion": "neutral",
        "audio_base64": audio_b64,
        "viseme_map": {
            v: speech_embodiment.viseme_to_expression(v)
            for v in ("AA", "EE", "OH", "FV", "BMP", "TH", "Rest")
        },
    }


@router.get("/speech/embodiment/skill")
async def get_embodiment_skill() -> dict[str, Any]:
    return SKILL_DEFINITION


@router.post("/speech/embodiment/memory/clear")
async def clear_embodiment_memory() -> dict[str, bool]:
    speech_embodiment.clear_memory()
    return {"ok": True}


@router.get("/speech/embodiment/memory")
async def get_embodiment_memory() -> dict[str, Any]:
    return {"history": speech_embodiment.get_dialogue_history()}


@router.get("/twins")
async def list_twins() -> list[dict]:
    return twins_competition.list_twins()


@router.get("/twins/leaderboard")
async def twins_leaderboard() -> list[dict]:
    return twins_competition.get_leaderboard()


@router.post("/twins/auto-add")
async def twins_auto_add() -> dict[str, Any]:
    from app.runtime import sdg_service

    t = twins_competition.auto_add_task(marketplace_service)
    if not t:
        raise HTTPException(status_code=500, detail="auto-add failed")
    sdg_service.track("tasks_created", 1)
    return {"status": "created", "task": t}


@router.post("/twins/allocate")
async def twins_allocate(data: dict) -> dict[str, Any]:
    task_id = data.get("task_id")
    twin_id = data.get("twin_id")
    if not task_id or not twin_id:
        raise HTTPException(status_code=400, detail="task_id and twin_id required")
    t = twins_competition.allocate_task(int(task_id), twin_id, marketplace_service)
    if not t:
        raise HTTPException(status_code=404, detail="task not available or twin not found")
    return {"status": "allocated", "task": t}


@router.post("/twins/teach")
async def twins_teach(data: dict) -> dict[str, Any]:
    teacher_id = data.get("teacher_id")
    student_id = data.get("student_id")
    skill_name = data.get("skill_name")
    if not teacher_id or not student_id or not skill_name:
        raise HTTPException(
            status_code=400,
            detail="teacher_id, student_id, and skill_name required",
        )
    result = twins_competition.teach_skill(teacher_id, student_id, skill_name)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="twin not found or teacher does not have that skill verified",
        )
    return {"status": "taught", **result}


@router.get("/competition/status")
async def competition_status(svc: TwinsServices = Depends(get_twins)) -> dict[str, Any]:
    return await svc.competition_status()


@router.post("/competition/submit")
async def competition_submit(
    payload: CompetitionSubmitRequest,
    svc: TwinsServices = Depends(get_twins),
) -> dict[str, Any]:
    return await svc.competition_submit(
        twin_id=payload.twin_id,
        round_id=payload.round_id,
        answer=payload.answer,
    )


@router.get("/bossbots")
async def list_bossbots(svc: TwinsServices = Depends(get_twins)) -> dict[str, Any]:
    return {"ok": True, "bossbots": svc.list_bossbots()}
