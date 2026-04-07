"""
Integration tests for runtime domain routes.

Covers the AOE-RUNTIME process manager REST API:
  - List services (GET /runtime/services)
  - Get service status (GET /runtime/services/{name})
  - Start / stop / restart / unlock (POST)
  - Log tail (GET /runtime/services/{name}/logs)
  - Health check (GET /runtime/health)
  - Port conflict scan (GET /runtime/conflicts)
  - Consolidation (POST /runtime/consolidate)
  - 404 on unknown service
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.runtime.router import router as runtime_router

# ─────────────────────────────────────────────────────────────────────────────
# Fake data
# ─────────────────────────────────────────────────────────────────────────────

FAKE_SVC = {
    "name": "bridge-auth",
    "status": "RUNNING",
    "pid": 12345,
    "port": 8080,
    "uptime": 3600,
}


def _make_mock_manager():
    m = MagicMock()
    m.list_services.return_value = [FAKE_SVC]
    m.status.return_value = {"ok": True, **FAKE_SVC}
    m.start = AsyncMock(return_value={"ok": True, **FAKE_SVC, "status": "RUNNING"})
    m.stop = AsyncMock(return_value={"ok": True, **FAKE_SVC, "status": "STOPPED"})
    m.restart = AsyncMock(return_value={"ok": True, **FAKE_SVC, "status": "RUNNING"})
    m.unlock.return_value = {"ok": True, "name": "bridge-auth", "status": "STOPPED"}
    m.logs.return_value = ["[INFO] service started", "[INFO] listening on :8080"]
    m.health_check.return_value = {"process": True, "port": True, "http": True}
    m.scan_conflicts.return_value = []
    m.run_consolidation = AsyncMock(return_value=[
        {"phase": 1, "ok": True, "services": ["bridge-auth"]},
        {"phase": 2, "ok": True, "services": ["bridge-revenue"]},
    ])
    return m


@pytest.fixture
def mock_mgr():
    return _make_mock_manager()


@pytest.fixture
async def client(mock_mgr):
    app = FastAPI()
    app.include_router(runtime_router)
    with patch("app.domains.runtime.router.get_manager", return_value=mock_mgr):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Service listing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_services(client, mock_mgr):
    resp = await client.get("/runtime/services")
    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert isinstance(data["services"], list)
    assert data["services"][0]["name"] == "bridge-auth"
    mock_mgr.list_services.assert_called_once()


@pytest.mark.asyncio
async def test_get_service(client, mock_mgr):
    resp = await client.get("/runtime/services/bridge-auth")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["name"] == "bridge-auth"
    mock_mgr.status.assert_called_once_with("bridge-auth")


@pytest.mark.asyncio
async def test_get_service_not_found(client, mock_mgr):
    mock_mgr.status.return_value = {"ok": False, "error": "service not found"}
    resp = await client.get("/runtime/services/nonexistent")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle operations
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_service(client, mock_mgr):
    resp = await client.post("/runtime/services/bridge-auth/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    mock_mgr.start.assert_called_once_with("bridge-auth")


@pytest.mark.asyncio
async def test_start_service_failure(client, mock_mgr):
    mock_mgr.start = AsyncMock(return_value={"ok": False, "error": "port already in use"})
    resp = await client.post("/runtime/services/bridge-auth/start")
    assert resp.status_code == 400
    assert "port" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_stop_service(client, mock_mgr):
    resp = await client.post("/runtime/services/bridge-auth/stop")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock_mgr.stop.assert_called_once_with("bridge-auth")


@pytest.mark.asyncio
async def test_restart_service(client, mock_mgr):
    resp = await client.post("/runtime/services/bridge-auth/restart")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock_mgr.restart.assert_called_once_with("bridge-auth")


@pytest.mark.asyncio
async def test_unlock_service(client, mock_mgr):
    resp = await client.post("/runtime/services/bridge-auth/unlock")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    mock_mgr.unlock.assert_called_once_with("bridge-auth")


@pytest.mark.asyncio
async def test_unlock_service_not_found(client, mock_mgr):
    mock_mgr.unlock.return_value = {"ok": False, "error": "unknown service"}
    resp = await client.post("/runtime/services/ghost/unlock")
    assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_logs(client, mock_mgr):
    resp = await client.get("/runtime/services/bridge-auth/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "bridge-auth"
    assert isinstance(data["lines"], list)
    assert data["count"] == 2
    mock_mgr.logs.assert_called_once_with("bridge-auth", lines=100)


@pytest.mark.asyncio
async def test_get_logs_custom_lines(client, mock_mgr):
    resp = await client.get("/runtime/services/bridge-auth/logs?lines=50")
    assert resp.status_code == 200
    mock_mgr.logs.assert_called_once_with("bridge-auth", lines=50)


# ─────────────────────────────────────────────────────────────────────────────
# Health and diagnostics
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_runtime_health(client, mock_mgr):
    resp = await client.get("/runtime/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert isinstance(data["services"], list)
    svc = data["services"][0]
    assert "process" in svc
    assert "port" in svc
    assert "http" in svc


@pytest.mark.asyncio
async def test_port_conflicts(client, mock_mgr):
    resp = await client.get("/runtime/conflicts")
    assert resp.status_code == 200
    data = resp.json()
    assert "conflicts" in data
    assert data["conflicts"] == []


@pytest.mark.asyncio
async def test_port_conflicts_detected(client, mock_mgr):
    mock_mgr.scan_conflicts.return_value = [
        {"port": 8080, "services": ["bridge-auth", "bridge-revenue"]}
    ]
    resp = await client.get("/runtime/conflicts")
    assert resp.status_code == 200
    assert len(resp.json()["conflicts"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Consolidation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consolidation_success(client, mock_mgr):
    resp = await client.post("/runtime/consolidate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert isinstance(data["phases"], list)
    assert len(data["phases"]) == 2
    mock_mgr.run_consolidation.assert_called_once()


@pytest.mark.asyncio
async def test_consolidation_partial_failure(client, mock_mgr):
    mock_mgr.run_consolidation = AsyncMock(return_value=[
        {"phase": 1, "ok": True, "services": ["bridge-auth"]},
        {"phase": 2, "ok": False, "services": ["bridge-revenue"], "error": "start failed"},
    ])
    resp = await client.post("/runtime/consolidate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False  # not all phases ok
