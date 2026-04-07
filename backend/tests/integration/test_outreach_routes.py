"""
Integration tests for outreach domain routes.

Covers the email queue pipeline (lead ingestion → outreach dispatch):
  - Enqueue job (POST /outreach/queue)
  - List queue with status filter (GET /outreach/queue)
  - Mark sent (POST /outreach/jobs/{id}/sent)
  - Mark failed (POST /outreach/jobs/{id}/failed)
  - History (GET /outreach/history)
  - Stats (GET /outreach/stats)
  - Auth guard on all endpoints
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.outreach.deps import get_outreach
from app.domains.outreach.router import router as outreach_router
from app.domains.outreach.services import OutreachService
from app.domains.infra.deps import require_jwt

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

FAKE_JOB = {
    "id": "job-001",
    "email": "cto@acme.com",
    "template": "intro",
    "status": "pending",
    "created_at": "2026-04-05T10:00:00Z",
    "attempts": 0,
}


def _make_mock_outreach():
    m = MagicMock(spec=OutreachService)
    m.enqueue = AsyncMock(return_value=FAKE_JOB)
    m.list_queue = AsyncMock(return_value=[FAKE_JOB])
    m.dispatch_pending = AsyncMock(return_value={"dispatched": 1, "errors": 0})
    m.mark_sent = AsyncMock(return_value={**FAKE_JOB, "status": "sent"})
    m.mark_failed = AsyncMock(return_value={**FAKE_JOB, "status": "failed", "error": "SMTP timeout"})
    m.history = AsyncMock(return_value=[FAKE_JOB])
    m.stats = AsyncMock(return_value={
        "pending": 1, "sent": 0, "failed": 0, "total": 1,
        "send_rate": 0.0, "fail_rate": 0.0,
    })
    return m


def _make_app(mock_outreach, override_jwt=True):
    app = FastAPI()
    app.include_router(outreach_router)
    app.dependency_overrides[get_outreach] = lambda: mock_outreach
    if override_jwt:
        app.dependency_overrides[require_jwt] = lambda: {"sub": "0xtest", "authority": "test"}
    return app


@pytest.fixture
def mock_outreach():
    return _make_mock_outreach()


@pytest.fixture
async def client(mock_outreach):
    app = _make_app(mock_outreach)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Queue operations
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enqueue_job(client, mock_outreach):
    resp = await client.post("/outreach/queue", json={
        "email": "cto@acme.com",
        "template": "intro",
        "lead_id": "lead-001",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["job"]["id"] == "job-001"
    mock_outreach.enqueue.assert_called_once()


@pytest.mark.asyncio
async def test_list_queue(client, mock_outreach):
    resp = await client.get("/outreach/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["count"] == 1
    assert isinstance(data["jobs"], list)


@pytest.mark.asyncio
async def test_list_queue_with_status_filter(client, mock_outreach):
    resp = await client.get("/outreach/queue?status=pending")
    assert resp.status_code == 200
    mock_outreach.list_queue.assert_called_with(status="pending")


@pytest.mark.asyncio
async def test_mark_sent(client, mock_outreach):
    resp = await client.post("/outreach/jobs/job-001/sent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["job"]["status"] == "sent"
    mock_outreach.mark_sent.assert_called_once_with("job-001")


@pytest.mark.asyncio
async def test_mark_sent_not_found(client, mock_outreach):
    mock_outreach.mark_sent = AsyncMock(return_value=None)
    resp = await client.post("/outreach/jobs/nonexistent/sent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_failed(client, mock_outreach):
    resp = await client.post("/outreach/jobs/job-001/failed", json={"error": "SMTP timeout"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["job"]["status"] == "failed"
    mock_outreach.mark_failed.assert_called_once_with("job-001", "SMTP timeout")


@pytest.mark.asyncio
async def test_mark_failed_not_found(client, mock_outreach):
    mock_outreach.mark_failed = AsyncMock(return_value=None)
    resp = await client.post("/outreach/jobs/nonexistent/failed", json={"error": "err"})
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# History and stats
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_history(client, mock_outreach):
    resp = await client.get("/outreach/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert isinstance(data["jobs"], list)


@pytest.mark.asyncio
async def test_history_limit(client, mock_outreach):
    resp = await client.get("/outreach/history?limit=10")
    assert resp.status_code == 200
    mock_outreach.history.assert_called_with(limit=10)


@pytest.mark.asyncio
async def test_stats(client, mock_outreach):
    resp = await client.get("/outreach/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "pending" in data
    assert "sent" in data
    assert "fail_rate" in data


# ─────────────────────────────────────────────────────────────────────────────
# Auth guard
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outreach_endpoints_require_auth(mock_outreach):
    app = _make_app(mock_outreach, override_jwt=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        endpoints = [
            ("GET",  "/outreach/queue"),
            ("POST", "/outreach/queue"),
            ("GET",  "/outreach/history"),
            ("GET",  "/outreach/stats"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = await ac.get(path)
            else:
                resp = await ac.post(path, json={"email": "x@y.com"})
            assert resp.status_code in (401, 403), \
                f"{method} {path} should require auth, got {resp.status_code}"
