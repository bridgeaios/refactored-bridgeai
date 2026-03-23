"""Integration tests for twins domain routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from app.domains.twins.router import router as twins_router
from app.domains.twins.deps import get_twins
from app.domains.twins.services import TwinsServices


def _mock_twins():
    m = MagicMock(spec=TwinsServices)
    m.get_profile = MagicMock(return_value={"twin_id": "default", "status": "active"})
    m.decide = AsyncMock(return_value={"ok": True, "decision": "proceed"})
    m.shared_xml = AsyncMock(return_value="<xml/>")
    m.emotion_status = AsyncMock(return_value={"twin_id": "default"})
    m.emotion_update = AsyncMock(return_value={"ok": True})
    m.speak = AsyncMock(return_value={"ok": True})
    m.competition_status = AsyncMock(return_value={"ok": True, "rounds": []})
    m.competition_submit = AsyncMock(return_value={"ok": True})
    m.list_bossbots = MagicMock(return_value=[])
    return m


@pytest.fixture
async def client():
    mock = _mock_twins()
    app = FastAPI()
    app.include_router(twins_router)
    app.dependency_overrides[get_twins] = lambda: mock
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_twin_profile(client):
    resp = await client.get("/twin/profile")
    assert resp.status_code == 200
    assert resp.json()["twin_id"] == "default"


@pytest.mark.asyncio
async def test_twin_decide(client):
    resp = await client.post("/twin/decide", json={"prompt": "What should I do?"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_emotion_status(client):
    resp = await client.get("/emotion/status")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_competition_status(client):
    resp = await client.get("/competition/status")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_bossbots(client):
    resp = await client.get("/bossbots")
    assert resp.status_code == 200
    assert "bossbots" in resp.json()
