"""
TTS domain router.
Ported from BRIDGE_AI_OS/core/app/routes/api.py -- TTS endpoints.

Endpoints:
  GET  /tts/available   -- check if cloud TTS is configured
  POST /tts/speak       -- text-to-speech synthesis
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.voice_broker import ELEVEN_API, LOCAL_TTS, VoiceBroker

router = APIRouter(prefix="/tts", tags=["tts"])

_voice_broker = VoiceBroker()


@router.get("/available")
async def tts_available() -> dict[str, Any]:
    """Check if cloud TTS is configured. Frontend skips POST when false, avoiding 503."""
    return {"available": bool(ELEVEN_API or LOCAL_TTS)}


@router.post("/speak")
async def tts_speak(payload: dict[str, Any]) -> Response:
    """Synthesize speech from text. Returns audio/mpeg stream."""
    text = payload.get("text") or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="text required")
    voice_id = payload.get("voice_id") or "21m00Tcm4TlvDq8ikWAM"
    try:
        chunks: list[bytes] = []
        async for chunk in _voice_broker.stream_tts(text[:1000], voice_id):
            chunks.append(chunk)
        return Response(b"".join(chunks), media_type="audio/mpeg")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
