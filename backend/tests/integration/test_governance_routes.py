"""Integration tests for governance domain routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from app.domains.governance.router import router as gov_router
from app.domains.governance.deps import get_governance
from app.domains.governance.services import GovernanceServices


def _mock_gov():
    m = MagicMock(spec=GovernanceServices)
    m.get_proposals = AsyncMock(return_value=[])
    m.submit_proposal = AsyncMock(return_value={"ok": True, "proposal_id": "p1"})
    m.vote = AsyncMock(return_value={"ok": True})
    m.get_reputation = MagicMock(return_value={"agent_id": "a1", "score": 0.8})
    m.sdg_status = AsyncMock(return_value={"ok": True, "sdgs": []})
    m.knowledge_graph_query = AsyncMock(return_value={"ok": True, "nodes": []})
    m.mission_board = AsyncMock(return_value={"ok": True})
    return m


@pytest.fixture
async def client():
    mock = _mock_gov()
    app = FastAPI()
    app.include_router(gov_router)
    app.dependency_overrides[get_governance] = lambda: mock
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_proposals(client):
    resp = await client.get("/governance/proposals")
    assert resp.status_code == 200
    assert "proposals" in resp.json()


@pytest.mark.asyncio
async def test_sdg_status(client):
    resp = await client.get("/sdg/status")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_mission_board(client):
    resp = await client.get("/mission/board")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_reputation(client):
    resp = await client.get("/reputation/agent-1")
    assert resp.status_code == 200
    assert "score" in resp.json()
