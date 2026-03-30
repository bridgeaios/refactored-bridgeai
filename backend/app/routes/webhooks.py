"""
Webhook ingestion router — bridge_real.py production implementation.

Endpoints:
  POST /api/lead    — ingest an external lead with optional value
  GET  /api/status  — real-time treasury + pipeline snapshot

Authentication:
  POST /lead uses X-Bridge-Webhook-Key header checked against
  BRIDGE_WEBHOOK_KEY env var (constant-time compare).
  If BRIDGE_WEBHOOK_KEY is unset the endpoint is disabled (503).

  GET /status requires a standard JWT (or BRIDGE_INTERNAL_TOKEN).
"""
from __future__ import annotations

import hmac
import os
import random
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.domains.infra.deps import require_jwt

router = APIRouter(tags=["webhooks"])


def _verify_webhook_key(request: Request) -> None:
    """Raise 401/503 if the webhook key header is missing or invalid.
    Key is read at call-time so hot-reload of env vars takes effect without restart.
    """
    key = os.environ.get("BRIDGE_WEBHOOK_KEY", "")
    if not key:
        raise HTTPException(503, detail="BRIDGE_WEBHOOK_KEY not configured")
    supplied = request.headers.get("X-Bridge-Webhook-Key", "")
    if not supplied or not hmac.compare_digest(supplied, key):
        raise HTTPException(401, detail="Invalid webhook key")


# ──────────────────────────────────────────────────────────────────────
# POST /api/lead  — bridge_real.py: @app.post("/lead")
# ──────────────────────────────────────────────────────────────────────

@router.post("/lead")
async def ingest_lead(request: Request) -> dict[str, Any]:
    """Accept an external lead push.

    Body (JSON):
      value      float  — estimated deal value (default 100)
      email      str    — contact email (optional)
      company    str    — company name (optional)
      industry   str    — industry tag (optional)
      source     str    — originating system (optional, default 'webhook')

    Header:
      X-Bridge-Webhook-Key: <BRIDGE_WEBHOOK_KEY>
    """
    _verify_webhook_key(request)

    try:
        data = await request.json()
    except Exception:
        data = {}

    value = float(data.get("value", 100))
    email = str(data.get("email", "") or f"lead_{int(__import__('time').time())}@external.invalid")
    company = str(data.get("company", "") or "")
    industry = str(data.get("industry", "") or "general")
    source = str(data.get("source", "webhook"))

    # Score: random in [0.5, 1.0] — mirrors bridge_real.py
    score = round(random.uniform(0.5, 1.0), 2)

    # Create CRM lead
    try:
        from app.domains.crm.deps import get_crm
        crm = get_crm()
        lead = await crm.create_lead({
            "email": email,
            "company": company,
            "industry": industry,
            "score": score,
            "source": source,
            "estimated_value": value,
        })
        lead_id = lead.get("id")
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Lead ingestion failed")
        raise HTTPException(500, detail="Lead ingestion failed") from e

    # Queue outreach
    try:
        from app.domains.outreach.deps import get_outreach
        outreach = get_outreach()
        await outreach.queue_email(
            email=email,
            company=company,
            template_type=industry,
        )
    except Exception:
        pass  # outreach is best-effort

    # Fire one activation loop cycle for immediate scoring/promotion
    try:
        from app.core.deps import get_memory
        import sys
        sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[4]))
        from workers import _activation_loop
        __import__('asyncio').ensure_future(_activation_loop(get_memory()))
    except Exception:
        pass  # non-critical — loop runs on its own schedule

    return {
        "status": "accepted",
        "lead_id": lead_id,
        "score": score,
        "email": email,
    }


# ──────────────────────────────────────────────────────────────────────
# GET /api/status  — bridge_real.py: @app.get("/status")
# ──────────────────────────────────────────────────────────────────────

@router.get("/status")
async def system_status(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Real-time system snapshot: treasury, leads, pipeline, trades.

    Maps bridge_real.py GET /status → treasury balance,
    extended with CRM pipeline and outreach queue counts.
    """
    from app.core.deps import get_memory

    mem = get_memory()

    # Treasury
    treasury_balance = 0.0
    try:
        from app.services.treasury import TreasuryService
        treasury_svc = TreasuryService(mem)
        ts = await treasury_svc.get_status()
        treasury_balance = ts.get("total_brdg", 0.0)
    except Exception:
        pass

    # CRM counts
    lead_count = 0
    stage_counts: dict[str, int] = {}
    try:
        from app.domains.crm.deps import get_crm
        crm = get_crm()
        stats = await crm.stats()
        lead_count = stats.get("total_leads", 0)
        stage_counts = stats.get("by_stage", {})
    except Exception:
        pass

    # Billing counts
    invoice_stats: dict[str, Any] = {}
    try:
        from app.domains.billing.deps import get_billing
        billing = get_billing()
        invoice_stats = await billing.stats()
    except Exception:
        pass

    # Outreach queue
    outreach_pending = 0
    try:
        from app.domains.outreach.deps import get_outreach
        outreach = get_outreach()
        ostat = await outreach.stats()
        outreach_pending = ostat.get("by_status", {}).get("pending", 0)
    except Exception:
        pass

    # Ledger trade count
    trade_count = 0
    try:
        from app.services.treasury import TreasuryService
        ledger = await TreasuryService(mem).get_ledger(limit=200)
        trade_count = sum(1 for e in ledger if e.get("method") == "trade")
    except Exception:
        pass

    return {
        "treasury": round(treasury_balance, 6),
        "leads": lead_count,
        "pipeline": stage_counts,
        "invoices": invoice_stats,
        "outreach_pending": outreach_pending,
        "trades": trade_count,
    }
