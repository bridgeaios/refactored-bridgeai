"""
Integration tests for TTS domain routes.

Covers the voice synthesis pipeline:
  - Availability check (GET /tts/available)
  - Speech synthesis (POST /tts/speak)
  - Empty text rejection
  - TTS backend unavailable (503)
  - Voice ID passthrough
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.tts.router import router as tts_router


async def _fake_stream(*args, **kwargs):
    """Async generator yielding fake audio chunks."""
    yield b"\xff\xfb\x90\x00"  # minimal MP3-like header bytes
    yield b"\x00" * 16


async def _empty_stream(*args, **kwargs):
    """Async generator that yields nothing — simulates silent broker."""
    return
    yield  # make it a generator


@pytest.fixture
async def client():
    app = FastAPI()
    app.include_router(tts_router)
    mock_broker = MagicMock()
    mock_broker.stream_tts = _fake_stream
    with patch("app.domains.tts.router._voice_broker", mock_broker):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def unavailable_client():
    """Client where VoiceBroker raises RuntimeError (no backend configured)."""
    app = FastAPI()
    app.include_router(tts_router)
    mock_broker = MagicMock()

    async def _raise(*args, **kwargs):
        raise RuntimeError("No TTS backend configured")
        yield  # make it a generator

    mock_broker.stream_tts = _raise
    with patch("app.domains.tts.router._voice_broker", mock_broker):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Availability
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tts_available_returns_bool(client):
    resp = await client.get("/tts/available")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert isinstance(data["available"], bool)


# ─────────────────────────────────────────────────────────────────────────────
# Speech synthesis
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tts_speak_returns_audio(client):
    resp = await client.post("/tts/speak", json={"text": "Hello, Bridge."})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert len(resp.content) > 0


@pytest.mark.asyncio
async def test_tts_speak_empty_text_rejected(client):
    resp = await client.post("/tts/speak", json={"text": ""})
    assert resp.status_code == 400
    assert "text" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_tts_speak_whitespace_only_rejected(client):
    resp = await client.post("/tts/speak", json={"text": "   "})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_tts_speak_backend_unavailable(unavailable_client):
    resp = await unavailable_client.post("/tts/speak", json={"text": "Hello"})
    assert resp.status_code == 503
    assert "TTS backend" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_tts_speak_voice_id_passthrough():
    """Custom voice_id is forwarded to the broker."""
    app = FastAPI()
    app.include_router(tts_router)
    mock_broker = MagicMock()
    captured: list = []

    async def _capture_stream(text, voice_id):
        captured.append(voice_id)
        yield b"\x00"

    mock_broker.stream_tts = _capture_stream
    with patch("app.domains.tts.router._voice_broker", mock_broker):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/tts/speak", json={"text": "Hello", "voice_id": "custom-voice-xyz"})

    assert captured == ["custom-voice-xyz"]


@pytest.mark.asyncio
async def test_tts_speak_default_voice_id():
    """When voice_id is omitted the default ElevenLabs voice is used."""
    app = FastAPI()
    app.include_router(tts_router)
    mock_broker = MagicMock()
    captured: list = []

    async def _capture_stream(text, voice_id):
        captured.append(voice_id)
        yield b"\x00"

    mock_broker.stream_tts = _capture_stream
    with patch("app.domains.tts.router._voice_broker", mock_broker):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/tts/speak", json={"text": "Hello"})

    assert captured == ["21m00Tcm4TlvDq8ikWAM"]
