"""
Integration tests for economy domain routes.
Uses httpx.AsyncClient against a minimal FastAPI app that includes only
the economy router, with EconomyServices dependency overridden.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.economy.deps import get_economy
from app.domains.economy.router import router as economy_router
from app.domains.economy.services import EconomyServices


def _make_mock_economy():
    m = MagicMock(spec=EconomyServices)
    m.collect = AsyncMock(return_value={"ok": True, "tx_id": "tx-1", "splits": {"ubi": 40}})
    m.treasury_status = AsyncMock(return_value={"total": 1000.0, "buckets": {}})
    m.treasury_ledger = AsyncMock(return_value=[])
    m.ubi_can_claim = AsyncMock(return_value=True)
    m.ubi_distribute = AsyncMock(return_value={"ok": True, "amount": 100})
    m.ubi_status = AsyncMock(return_value={"can_claim": True, "amount": 100, "period_seconds": 86400})
    m.get_tasks = MagicMock(return_value=[])
    m.post_task = MagicMock(return_value={"ok": True, "task_id": 1, "task": {"id": 1}})
    m.accept_task = MagicMock(return_value={"ok": True, "task": {"id": 1}})
    m.complete_task = MagicMock(return_value={"ok": True, "task": {"id": 1}})
    m.revenue_summary = AsyncMock(return_value={"total": 0.0})
    return m


@pytest.fixture
def mock_economy():
    return _make_mock_economy()


@pytest.fixture
async def client(mock_economy):
    app = FastAPI()
    app.include_router(economy_router)
    app.dependency_overrides[get_economy] = lambda: mock_economy
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_treasury_collect(client, mock_economy):
    resp = await client.post("/treasury/collect", json={"amount": 100.0})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock_economy.collect.assert_called_once()


@pytest.mark.asyncio
async def test_treasury_status(client):
    resp = await client.get("/treasury/status")
    assert resp.status_code == 200
    assert "total" in resp.json()


@pytest.mark.asyncio
async def test_treasury_ledger(client):
    resp = await client.get("/treasury/ledger")
    assert resp.status_code == 200
    assert "ledger" in resp.json()


@pytest.mark.asyncio
async def test_marketplace_open(client):
    resp = await client.get("/marketplace/open")
    assert resp.status_code == 200
    assert "tasks" in resp.json()


@pytest.mark.asyncio
async def test_marketplace_post_task(client, mock_economy):
    resp = await client.post("/marketplace/post", json={"title": "Build widget", "value": 50.0})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_ubi_status(client):
    resp = await client.get("/ubi/status?address=0xABC")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_ubi_claim(client, mock_economy):
    resp = await client.post("/ubi/claim", json={"address": "0xABC"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_revenue_summary(client):
    resp = await client.get("/revenue/summary")
    assert resp.status_code == 200
