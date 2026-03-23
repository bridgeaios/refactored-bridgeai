import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.domains.network.deps import get_network
from app.domains.network.router import router as network_router
from app.domains.network.services import NetworkServices


def _mock_net():
    m = MagicMock(spec=NetworkServices)
    m.network_status = AsyncMock(return_value={"ok": True, "swarm": {}, "projects": 0})
    m.swarm_health = AsyncMock(return_value={"ok": True, "nodes": [], "healthy": True})
    m.swarm_broadcast = AsyncMock(return_value={"ok": True, "channel": "test"})
    m.list_projects = AsyncMock(return_value=[])
    m.register_project = AsyncMock(return_value={"ok": True, "project_id": "p1"})
    return m


@pytest.fixture
async def client():
    mock = _mock_net()
    app = FastAPI()
    app.include_router(network_router)
    app.dependency_overrides[get_network] = lambda: mock
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_network_status(client):
    resp = await client.get("/network/status")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_swarm_health(client):
    resp = await client.get("/swarm/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_projects(client):
    resp = await client.get("/projects")
    assert resp.status_code == 200
    assert "projects" in resp.json()
