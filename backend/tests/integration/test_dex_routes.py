"""
Integration tests for DEX domain routes.

Covers the BRDG token swap pipeline:
  - Balance query (GET /dex/balance/{address})
  - Swap rates (GET /dex/rates)
  - Swap execution (POST /dex/swap)
  - Trade alias (POST /dex/trade)
  - Trading signals (GET /dex/signals)
  - Input validation
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.dex.router import router as dex_router
from app.domains.infra.deps import require_jwt

# ─────────────────────────────────────────────────────────────────────────────
# Fake data
# ─────────────────────────────────────────────────────────────────────────────

FAKE_RATES = {"ETH": 0.0003, "SOL": 0.002, "USDC": 0.15, "USDT": 0.15, "MATIC": 0.2}

FAKE_SWAP_OK = {
    "ok": True,
    "address": "0xabc",
    "from_token": "BRDG",
    "to_token": "ETH",
    "amount_in": 100.0,
    "amount_out": 0.03,
    "tx_id": "tx-001",
}


def _make_mock_service():
    m = MagicMock()
    m.get_balance.return_value = 500.0
    m.get_rates.return_value = FAKE_RATES
    m.swap.return_value = FAKE_SWAP_OK
    return m


def _make_app(mock_svc):
    app = FastAPI()
    app.include_router(dex_router)
    return app


@pytest.fixture
def mock_svc():
    return _make_mock_service()


@pytest.fixture
async def client(mock_svc):
    app = _make_app(mock_svc)
    app.dependency_overrides[require_jwt] = lambda: {"sub": "0xtest", "authority": "test"}
    with patch("app.domains.dex.router.dex_service", mock_svc):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Balance
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dex_balance(client, mock_svc):
    resp = await client.get("/dex/balance/0xabc")
    assert resp.status_code == 200
    assert resp.json()["balance"] == 500.0
    mock_svc.get_balance.assert_called_once_with("0xabc")


@pytest.mark.asyncio
async def test_dex_balance_unknown_address():
    """Unknown address returns balance of 0 (real service behaviour)."""
    from app.domains.dex.services import DexService
    svc = DexService()
    assert svc.get_balance("unknown-wallet") == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Rates
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dex_rates(client, mock_svc):
    resp = await client.get("/dex/rates")
    assert resp.status_code == 200
    data = resp.json()
    assert "ETH" in data
    assert "USDC" in data
    mock_svc.get_rates.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Swap
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dex_swap_success(client, mock_svc):
    resp = await client.post("/dex/swap", json={
        "address": "0xabc",
        "from_token": "BRDG",
        "to_token": "ETH",
        "amount": 100.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["to_token"] == "ETH"
    mock_svc.swap.assert_called_once_with("0xabc", "BRDG", "ETH", 100.0)


@pytest.mark.asyncio
async def test_dex_swap_missing_address(client):
    resp = await client.post("/dex/swap", json={"to_token": "ETH", "amount": 10})
    assert resp.status_code == 400
    assert "address" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_dex_swap_missing_to_token(client):
    resp = await client.post("/dex/swap", json={"address": "0xabc", "amount": 10})
    assert resp.status_code == 400
    assert "to_token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_dex_swap_invalid_amount(client):
    resp = await client.post("/dex/swap", json={
        "address": "0xabc", "to_token": "ETH", "amount": "not-a-number"
    })
    assert resp.status_code == 400
    assert "amount" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_dex_swap_service_failure(client, mock_svc):
    mock_svc.swap.return_value = {"ok": False, "error": "Insufficient balance"}
    resp = await client.post("/dex/swap", json={
        "address": "0xpoor", "to_token": "ETH", "amount": 9999.0
    })
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# Trade alias
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dex_trade_success(client, mock_svc):
    resp = await client.post("/dex/trade", json={
        "asset": "USDC",
        "address": "0xabc",
        "amount": 50.0,
    })
    assert resp.status_code == 200
    mock_svc.swap.assert_called_once_with("0xabc", "BRDG", "USDC", 50.0)


@pytest.mark.asyncio
async def test_dex_trade_missing_asset(client):
    resp = await client.post("/dex/trade", json={"address": "0xabc", "amount": 10})
    assert resp.status_code == 400
    assert "asset" in resp.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# Signals
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dex_signals(client, mock_svc):
    resp = await client.get("/dex/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert isinstance(data["signals"], list)
    assert len(data["signals"]) == len(FAKE_RATES)
    first = data["signals"][0]
    assert "pair" in first
    assert "rate" in first
    assert "signal" in first
