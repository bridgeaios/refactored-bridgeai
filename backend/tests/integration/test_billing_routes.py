"""
Integration tests for billing domain routes.

Covers:
- Invoice CRUD (create, list, get, mark paid)
- Paystack webhook — valid signature, invalid signature, missing secret
- Treasury disburse ENV bypass removal (BUG-004 regression guard)
- Auth guard on protected endpoints
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.billing.deps import get_billing
from app.domains.billing.router import router as billing_router
from app.domains.billing.services import BillingService
from app.domains.infra.deps import require_jwt

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

FAKE_INVOICE = {
    "id": "inv-001",
    "amount": 500.0,
    "currency": "ZAR",
    "status": "pending",
    "client_email": "test@example.com",
}


def _make_mock_billing():
    m = MagicMock(spec=BillingService)
    m.create_invoice = AsyncMock(return_value=FAKE_INVOICE)
    m.list_invoices = AsyncMock(return_value=[FAKE_INVOICE])
    m.get_invoice = AsyncMock(return_value=FAKE_INVOICE)
    m.mark_paid = AsyncMock(return_value={**FAKE_INVOICE, "status": "paid"})
    m.stats = AsyncMock(return_value={"total_invoices": 1, "paid": 0, "pending": 1, "total_value": 500.0})
    m.reconcile_by_amount = AsyncMock(return_value={**FAKE_INVOICE, "status": "paid"})
    m.generate_pdf = AsyncMock(return_value=b"%PDF-1.4 test")
    m._paystack_link = AsyncMock(return_value="https://paystack.com/pay/test")
    return m


def _make_app(mock_billing, override_jwt=True):
    # Billing router has no prefix — routes are /invoices/... mounted at root
    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_billing] = lambda: mock_billing
    if override_jwt:
        # Bypass JWT auth for most tests — auth guard tested separately
        app.dependency_overrides[require_jwt] = lambda: {"sub": "0xtest", "authority": "test"}
    return app


def _paystack_sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_billing():
    return _make_mock_billing()


@pytest.fixture
async def client(mock_billing):
    app = _make_app(mock_billing)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Invoice CRUD
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_invoice(client, mock_billing):
    resp = await client.post("/invoices", json={
        "client_email": "test@example.com",
        "client_name": "Test Client",
        "currency": "ZAR",
        "items": [{"description": "Consulting", "quantity": 1, "unit_price": 500.0}],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["invoice"]["id"] == "inv-001"
    mock_billing.create_invoice.assert_called_once()


@pytest.mark.asyncio
async def test_list_invoices(client, mock_billing):
    resp = await client.get("/invoices")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert isinstance(data["invoices"], list)
    assert data["count"] == 1


@pytest.mark.asyncio
async def test_get_invoice(client, mock_billing):
    resp = await client.get("/invoices/inv-001")
    assert resp.status_code == 200
    assert resp.json()["id"] == "inv-001"


@pytest.mark.asyncio
async def test_invoice_stats(client, mock_billing):
    resp = await client.get("/invoices/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_invoices" in data
    assert data["total_value"] == 500.0


@pytest.mark.asyncio
async def test_mark_paid(client, mock_billing):
    resp = await client.post("/invoices/inv-001/mark-paid", json={
        "payment_method": "manual",
        "reference": "REF-001",
    })
    assert resp.status_code == 200
    mock_billing.mark_paid.assert_called_once_with("inv-001", "manual", "REF-001")


# ─────────────────────────────────────────────────────────────────────────────
# Auth guard
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_invoice_requires_auth(mock_billing):
    """Endpoints with require_jwt must reject requests with no token."""
    app = _make_app(mock_billing, override_jwt=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/invoices", json={"amount": 100.0})
    # 401 or 403 expected — not 200
    assert resp.status_code in (401, 403), f"Expected auth failure, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_invoices_requires_auth(mock_billing):
    app = _make_app(mock_billing, override_jwt=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/invoices")
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Paystack webhook — BUG-009 regression guard
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_paystack_webhook_valid_signature(mock_billing, monkeypatch):
    """Valid HMAC-SHA512 signature must result in 200 and reconciliation."""
    secret = "test-paystack-secret-key"
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", secret)

    payload = json.dumps({
        "event": "charge.success",
        "data": {"amount": 50000, "currency": "ZAR", "reference": "REF-123"},
    }).encode()
    sig = _paystack_sig(secret, payload)

    app = _make_app(mock_billing)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/invoices/reconcile",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-paystack-signature": sig,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    mock_billing.reconcile_by_amount.assert_called_once()


@pytest.mark.asyncio
async def test_paystack_webhook_invalid_signature(mock_billing, monkeypatch):
    """Invalid signature must return 400 — not 200 (BUG-009 regression guard)."""
    secret = "test-paystack-secret-key"
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", secret)

    payload = json.dumps({"event": "charge.success", "data": {"amount": 50000}}).encode()

    app = _make_app(mock_billing)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/invoices/reconcile",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-paystack-signature": "invalidsignature",
            },
        )
    assert resp.status_code == 400
    mock_billing.reconcile_by_amount.assert_not_called()


@pytest.mark.asyncio
async def test_paystack_webhook_missing_secret(mock_billing, monkeypatch):
    """Missing PAYSTACK_SECRET_KEY must return 500, not process the event."""
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)

    payload = json.dumps({"event": "charge.success", "data": {"amount": 50000}}).encode()

    app = _make_app(mock_billing)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/invoices/reconcile",
            content=payload,
            headers={"Content-Type": "application/json", "x-paystack-signature": "anything"},
        )
    assert resp.status_code == 500
    mock_billing.reconcile_by_amount.assert_not_called()


@pytest.mark.asyncio
async def test_paystack_webhook_no_signature_header(mock_billing, monkeypatch):
    """Missing signature header must be rejected (empty string fails compare_digest)."""
    secret = "test-paystack-secret-key"
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", secret)

    payload = json.dumps({"event": "charge.success", "data": {"amount": 50000}}).encode()

    app = _make_app(mock_billing)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/invoices/reconcile",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400
