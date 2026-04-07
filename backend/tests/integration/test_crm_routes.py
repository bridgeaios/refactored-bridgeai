"""
Integration tests for CRM domain routes.

Covers the full lead-to-deal revenue pipeline:
  - Lead ingestion (POST /crm/leads)
  - Lead listing and filtering (GET /crm/leads)
  - Lead detail (GET /crm/leads/{id})
  - Stage update (PUT /crm/leads/{id}/stage)
  - Note creation (POST /crm/leads/{id}/notes)
  - Pipeline view (GET /crm/pipeline)
  - Stats (GET /crm/stats)
  - Deal creation (POST /crm/deals)
  - Deal detail (GET /crm/deals/{id})
  - Mark deal won (POST /crm/deals/{id}/won)
  - Auth guard — all endpoints require JWT
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.billing.deps import get_billing
from app.domains.crm.deps import get_crm
from app.domains.crm.router import router as crm_router
from app.domains.crm.services import CrmService
from app.domains.infra.deps import require_jwt

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

FAKE_LEAD = {
    "id": "lead-001",
    "email": "cto@acme.com",
    "company": "Acme Corp",
    "name": "John Smith",
    "phone": "",
    "source": "scraper",
    "stage": "new",
    "score": 0.72,
    "industry": "tech",
    "size_estimate": "mid",
    "pain_points": ["scaling", "automation"],
    "template_type": "saas",
    "created_at": "2026-04-05T10:00:00Z",
    "updated_at": "2026-04-05T10:00:00Z",
    "activities": [],
    "ok": True,
    "duplicate": False,
}

FAKE_DEAL = {
    "id": "deal-001",
    "lead_id": "lead-001",
    "title": "Acme SaaS subscription",
    "value": 1200.0,
    "currency": "ZAR",
    "status": "open",
}


def _make_mock_crm():
    m = MagicMock(spec=CrmService)
    m.ingest_lead = AsyncMock(return_value={**FAKE_LEAD, "ok": True, "duplicate": False})
    m.get_lead = AsyncMock(return_value=FAKE_LEAD)
    m.list_leads = AsyncMock(return_value=[FAKE_LEAD])
    m.update_stage = AsyncMock(return_value={**FAKE_LEAD, "stage": "qualified"})
    m.add_note = AsyncMock(return_value={**FAKE_LEAD, "activities": [{"type": "note", "text": "Called them"}]})
    m.pipeline = AsyncMock(return_value={
        "new": [FAKE_LEAD], "qualified": [], "proposal": [],
        "negotiation": [], "won": [], "lost": [],
    })
    m.stats = AsyncMock(return_value={
        "total_leads": 1, "by_stage": {"new": 1}, "avg_score": 0.72,
        "conversion_rate": 0.0, "total_deals": 0, "pipeline_value": 0.0,
    })
    m.create_deal = AsyncMock(return_value=FAKE_DEAL)
    m.get_deal = AsyncMock(return_value=FAKE_DEAL)
    m.mark_deal_won = AsyncMock(return_value={**FAKE_DEAL, "status": "won"})
    return m


def _make_app(mock_crm, override_jwt=True):
    app = FastAPI()
    app.include_router(crm_router)
    app.dependency_overrides[get_crm] = lambda: mock_crm
    # Billing dep is injected into CRM router for deal→invoice linking
    mock_billing = MagicMock()
    mock_billing.create_invoice = AsyncMock(return_value={"id": "inv-001", "invoice_number": "INV-001"})
    app.dependency_overrides[get_billing] = lambda: mock_billing
    if override_jwt:
        app.dependency_overrides[require_jwt] = lambda: {"sub": "0xtest", "authority": "test"}
    return app


@pytest.fixture
def mock_crm():
    return _make_mock_crm()


@pytest.fixture
async def client(mock_crm):
    app = _make_app(mock_crm)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Lead ingestion — revenue entry point
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_lead(client, mock_crm):
    resp = await client.post("/crm/leads", json={
        "email": "cto@acme.com",
        "company": "Acme Corp",
        "name": "John Smith",
        "source": "scraper",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["id"] == "lead-001"
    assert data["duplicate"] is False
    mock_crm.ingest_lead.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_lead_missing_email_rejected(client):
    """Email is required — missing it should return 422."""
    resp = await client.post("/crm/leads", json={"company": "Acme"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_duplicate_lead(client, mock_crm):
    """Duplicate leads (same email) return ok=True with duplicate=True."""
    mock_crm.ingest_lead = AsyncMock(return_value={**FAKE_LEAD, "ok": True, "duplicate": True})
    resp = await client.post("/crm/leads", json={"email": "cto@acme.com", "company": "Acme"})
    assert resp.status_code == 200
    assert resp.json()["duplicate"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Lead reads
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_leads(client, mock_crm):
    resp = await client.get("/crm/leads")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["count"] == 1
    assert isinstance(data["leads"], list)


@pytest.mark.asyncio
async def test_list_leads_with_stage_filter(client, mock_crm):
    resp = await client.get("/crm/leads?stage=new")
    assert resp.status_code == 200
    mock_crm.list_leads.assert_called_with(
        stage="new", source=None, min_score=None, limit=100, offset=0
    )


@pytest.mark.asyncio
async def test_get_lead(client, mock_crm):
    resp = await client.get("/crm/leads/lead-001")
    assert resp.status_code == 200
    assert resp.json()["id"] == "lead-001"
    assert resp.json()["score"] == 0.72


@pytest.mark.asyncio
async def test_get_lead_not_found(client, mock_crm):
    mock_crm.get_lead = AsyncMock(return_value=None)
    resp = await client.get("/crm/leads/nonexistent")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Stage progression — sales pipeline movement
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_stage(client, mock_crm):
    resp = await client.put("/crm/leads/lead-001/stage", json={"stage": "qualified", "note": "Good fit"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["lead"]["stage"] == "qualified"
    mock_crm.update_stage.assert_called_once_with("lead-001", "qualified", "Good fit")


@pytest.mark.asyncio
async def test_update_stage_invalid_value(client):
    """Stage must match the allowed enum — invalid values return 422."""
    resp = await client.put("/crm/leads/lead-001/stage", json={"stage": "invalid_stage"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_note(client, mock_crm):
    resp = await client.post("/crm/leads/lead-001/notes", json={"text": "Called them, interested"})
    assert resp.status_code == 200
    mock_crm.add_note.assert_called_once_with("lead-001", "Called them, interested")


@pytest.mark.asyncio
async def test_add_empty_note_rejected(client):
    resp = await client.post("/crm/leads/lead-001/notes", json={"text": ""})
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline and stats
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline(client, mock_crm):
    resp = await client.get("/crm/pipeline")
    assert resp.status_code == 200
    data = resp.json()
    for stage in ("new", "qualified", "proposal", "negotiation", "won", "lost"):
        assert stage in data


@pytest.mark.asyncio
async def test_crm_stats(client, mock_crm):
    resp = await client.get("/crm/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_leads" in data
    assert "avg_score" in data
    assert "conversion_rate" in data


# ─────────────────────────────────────────────────────────────────────────────
# Deal lifecycle — lead→deal conversion
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_deal(client, mock_crm):
    resp = await client.post("/crm/deals", json={
        "lead_id": "lead-001",
        "title": "Acme SaaS subscription",
        "value": 1200.0,
        "currency": "ZAR",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["deal"]["id"] == "deal-001"
    assert data["deal"]["value"] == 1200.0
    mock_crm.create_deal.assert_called_once()


@pytest.mark.asyncio
async def test_get_deal(client, mock_crm):
    resp = await client.get("/crm/deals/deal-001")
    assert resp.status_code == 200
    assert resp.json()["id"] == "deal-001"


@pytest.mark.asyncio
async def test_mark_deal_won(client, mock_crm):
    resp = await client.post("/crm/deals/deal-001/won", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["deal"]["status"] == "won"
    mock_crm.mark_deal_won.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# Auth guard — all CRM endpoints require JWT
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lead_endpoints_require_auth(mock_crm):
    app = _make_app(mock_crm, override_jwt=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for method, path, body in [
            ("GET",  "/crm/leads",    None),
            ("POST", "/crm/leads",    {"email": "x@y.com"}),
            ("GET",  "/crm/pipeline", None),
            ("GET",  "/crm/stats",    None),
        ]:
            if method == "GET":
                resp = await ac.get(path)
            else:
                resp = await ac.post(path, json=body)
            assert resp.status_code in (401, 403), \
                f"{method} {path} should require auth, got {resp.status_code}"
