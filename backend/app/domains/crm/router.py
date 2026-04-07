"""CRM domain router — leads, pipeline, deals, CSV import/export, AI suggestions."""
from __future__ import annotations

import csv
import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.domains.billing.deps import get_billing
from app.domains.billing.services import BillingService
from app.domains.crm.deps import get_crm
from app.domains.crm.models import DealCreate, LeadIngest, NoteCreate, StageUpdate
from app.domains.crm.services import CrmService
from app.domains.infra.deps import require_jwt

log = logging.getLogger(__name__)

router = APIRouter(tags=["crm"])

CrmDep     = Annotated[CrmService,     Depends(get_crm)]
BillingDep = Annotated[BillingService, Depends(get_billing)]


# ------------------------------------------------------------------
# Lead ingestion — called by workers.py scraper (JWT required)
# ------------------------------------------------------------------

@router.post("/crm/leads")
async def ingest_lead(
    payload: LeadIngest,
    svc: CrmDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    result = await svc.ingest_lead(payload.model_dump())
    return result


# ------------------------------------------------------------------
# Lead reads — authenticated
# ------------------------------------------------------------------

@router.get("/crm/leads")
async def list_leads(
    svc: CrmDep,
    _: dict = Depends(require_jwt),
    stage: str | None = None,
    source: str | None = None,
    min_score: float | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    leads = await svc.list_leads(
        stage=stage, source=source, min_score=min_score,
        limit=limit, offset=offset,
    )
    return {"ok": True, "leads": leads, "count": len(leads)}


@router.get("/crm/leads/{lead_id}")
async def get_lead(lead_id: str, svc: CrmDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    lead = await svc.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, detail="Lead not found")
    return lead


# ------------------------------------------------------------------
# Pipeline mutations
# ------------------------------------------------------------------

@router.put("/crm/leads/{lead_id}/stage")
async def update_stage(
    lead_id: str,
    payload: StageUpdate,
    svc: CrmDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    updated = await svc.update_stage(lead_id, payload.stage, payload.note)
    if not updated:
        raise HTTPException(404, detail="Lead not found")
    return {"ok": True, "lead": updated}


@router.post("/crm/leads/{lead_id}/notes")
async def add_note(
    lead_id: str,
    payload: NoteCreate,
    svc: CrmDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    updated = await svc.add_note(lead_id, payload.text)
    if not updated:
        raise HTTPException(404, detail="Lead not found")
    return {"ok": True, "lead": updated}


# ------------------------------------------------------------------
# Pipeline overview + stats
# ------------------------------------------------------------------

@router.get("/crm/pipeline")
async def pipeline(svc: CrmDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    return await svc.pipeline()


@router.get("/crm/stats")
async def stats(svc: CrmDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    return await svc.stats()


# ------------------------------------------------------------------
# Deals
# ------------------------------------------------------------------

@router.post("/crm/deals")
async def create_deal(
    payload: DealCreate,
    svc: CrmDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    deal = await svc.create_deal(
        lead_id=payload.lead_id,
        title=payload.title,
        value=payload.value,
        currency=payload.currency,
    )
    if not deal:
        raise HTTPException(404, detail="Lead not found")
    return {"ok": True, "deal": deal}


@router.get("/crm/deals/{deal_id}")
async def get_deal(deal_id: str, svc: CrmDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    deal = await svc.get_deal(deal_id)
    if not deal:
        raise HTTPException(404, detail="Deal not found")
    return deal


@router.post("/crm/deals/{deal_id}/won")
async def mark_deal_won(
    deal_id: str,
    svc: CrmDep,
    billing: BillingDep,
    claims: dict = Depends(require_jwt),
) -> dict[str, Any]:
    """Mark deal won and auto-create a draft invoice from deal data."""
    deal = await svc.mark_deal_won(deal_id, invoice_id=None)
    if not deal:
        raise HTTPException(404, detail="Deal not found")

    # Auto-create draft invoice from deal metadata
    invoice: dict[str, Any] | None = None
    try:
        value = float(deal.get("value") or deal.get("deal_value") or 0)
        if value > 0:
            invoice_payload: dict[str, Any] = {
                "deal_id":        deal_id,
                "lead_id":        deal.get("lead_id"),
                "client_name":    deal.get("client_name") or deal.get("company") or "",
                "client_email":   deal.get("client_email") or deal.get("email") or "",
                "client_company": deal.get("company") or "",
                "currency":       deal.get("currency", "ZAR"),
                "due_days":       30,
                "notes":          f"Auto-generated from CRM deal {deal_id} (marked won by {claims.get('sub', 'unknown')})",
                "items": [{
                    "description": deal.get("title") or deal.get("name") or "Professional Services",
                    "quantity":    1,
                    "unit_price":  value,
                }],
            }
            invoice = await billing.create_invoice(invoice_payload)
            # Link invoice back to deal
            await svc.mark_deal_won(deal_id, invoice_id=invoice["id"])
            log.info("Auto-invoice %s created for won deal %s (%.2f %s)",
                     invoice["invoice_number"], deal_id, value, invoice_payload["currency"])
    except Exception as exc:
        # Invoice failure must not block the deal-won transition
        log.error("Auto-invoice creation failed for deal %s: %s", deal_id, exc)

    # Discord notification — fire-and-forget
    import asyncio
    from app.services.discord_notify import notify as _discord
    asyncio.create_task(_discord("deal_won", {
        "deal_id": deal_id,
        "client":  deal.get("client_name") or deal.get("company", ""),
        "amount":  deal.get("value") or deal.get("deal_value", 0),
        "invoice": invoice.get("invoice_number", "") if invoice else "",
    }))

    return {"ok": True, "deal": deal, "invoice": invoice}


# ------------------------------------------------------------------
# CSV columns in canonical order
# ------------------------------------------------------------------
_CSV_COLS = [
    "email", "name", "company", "phone", "industry",
    "source", "stage", "score", "pain_points", "notes",
]

_DUMMY_ROWS = [
    {
        "email": "sarah.johnson@techventures.co.za",
        "name": "Sarah Johnson",
        "company": "TechVentures SA",
        "phone": "+27 82 555 0101",
        "industry": "tech",
        "source": "linkedin",
        "stage": "qualified",
        "score": "0.82",
        "pain_points": "manual reporting;slow onboarding",
        "notes": "Demo scheduled for Q2",
    },
    {
        "email": "mark.olivier@finbridge.co.za",
        "name": "Mark Olivier",
        "company": "FinBridge Capital",
        "phone": "+27 11 555 0202",
        "industry": "finance",
        "source": "referral",
        "stage": "proposal",
        "score": "0.74",
        "pain_points": "compliance gaps;legacy systems",
        "notes": "Requires NDA before proposal",
    },
    {
        "email": "amina.hassan@greenloop.co.za",
        "name": "Amina Hassan",
        "company": "GreenLoop Consulting",
        "phone": "+27 21 555 0303",
        "industry": "consulting",
        "source": "website",
        "stage": "new",
        "score": "0.61",
        "pain_points": "no AI tooling",
        "notes": "",
    },
]


# ------------------------------------------------------------------
# CSV template download (dummy data for reference)
# ------------------------------------------------------------------

@router.get("/crm/contacts/template")
async def download_csv_template(_: dict = Depends(require_jwt)) -> StreamingResponse:
    """Download a sample CSV with dummy contact data to use as import template."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_COLS)
    writer.writeheader()
    for row in _DUMMY_ROWS:
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="contacts_template.csv"'},
    )


# ------------------------------------------------------------------
# CSV export — all contacts
# ------------------------------------------------------------------

@router.get("/crm/contacts/export")
async def export_contacts_csv(
    svc: CrmDep,
    _: dict = Depends(require_jwt),
) -> StreamingResponse:
    leads = await svc.list_leads(limit=5000)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_COLS, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        row = {
            "email": lead.get("email", ""),
            "name": lead.get("name", ""),
            "company": lead.get("company", ""),
            "phone": lead.get("phone", ""),
            "industry": lead.get("industry", ""),
            "source": lead.get("source", ""),
            "stage": lead.get("stage", ""),
            "score": str(round(lead.get("score", 0), 3)),
            "pain_points": ";".join(lead.get("pain_points", [])),
            "notes": "",
        }
        writer.writerow(row)
    buf.seek(0)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="contacts_{date_str}.csv"'},
    )


# ------------------------------------------------------------------
# CSV import — bulk create contacts
# ------------------------------------------------------------------

@router.post("/crm/contacts/import")
async def import_contacts_csv(
    svc: CrmDep,
    _: dict = Depends(require_jwt),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, detail="Only CSV files are accepted")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, detail="CSV has no headers")

    # Normalise header names (lowercase, strip spaces)
    normalised_fields = [f.strip().lower() for f in reader.fieldnames]

    if "email" not in normalised_fields:
        raise HTTPException(400, detail="CSV must contain an 'email' column")

    created = skipped = errors = 0
    error_details: list[str] = []

    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        email = norm_row.get("email", "").strip().lower()
        if not email:
            skipped += 1
            continue

        # Parse pain_points — semicolon or comma separated
        raw_pains = norm_row.get("pain_points", "")
        pains = [p.strip() for p in raw_pains.replace(",", ";").split(";") if p.strip()]

        try:
            score_raw = float(norm_row.get("score", "0") or "0")
        except ValueError:
            score_raw = 0.0

        payload = {
            "email": email,
            "name": norm_row.get("name", ""),
            "company": norm_row.get("company", ""),
            "phone": norm_row.get("phone", ""),
            "source": norm_row.get("source", "csv_import"),
            "osint_profile": {
                "industry": norm_row.get("industry", "unknown"),
                "pain_points": pains,
                "profile_confidence": min(score_raw, 1.0),
                "template_type": "generic",
            },
        }

        try:
            result = await svc.ingest_lead(payload)
            if result.get("duplicate"):
                skipped += 1
            else:
                created += 1
        except Exception as exc:
            errors += 1
            if len(error_details) < 5:
                error_details.append(f"Row {i}: {exc}")

    return {
        "ok": True,
        "created": created,
        "skipped_duplicates": skipped,
        "errors": errors,
        "error_details": error_details,
    }


# ------------------------------------------------------------------
# Import contacts from Lead Gen module
# ------------------------------------------------------------------

@router.post("/crm/contacts/import-from-leads")
async def import_from_leadgen(
    svc: CrmDep,
    _: dict = Depends(require_jwt),
    stage: str | None = None,
    min_score: float = 0.0,
    limit: int = 100,
) -> dict[str, Any]:
    """Re-ingest existing leads into CRM contacts (idempotent — deduplication prevents doubles)."""
    leads = await svc.list_leads(stage=stage, min_score=min_score, limit=limit)
    imported = 0
    for lead in leads:
        result = await svc.ingest_lead({
            "email": lead.get("email", ""),
            "name": lead.get("name", ""),
            "company": lead.get("company", ""),
            "phone": lead.get("phone", ""),
            "source": lead.get("source", "leadgen"),
            "osint_profile": lead.get("osint_profile", {}),
        })
        if not result.get("duplicate"):
            imported += 1
    return {"ok": True, "imported": imported, "total_leads": len(leads)}


# ------------------------------------------------------------------
# AI suggestions for a specific lead/contact
# ------------------------------------------------------------------

@router.get("/crm/leads/{lead_id}/ai-suggestions")
async def lead_ai_suggestions(
    lead_id: str,
    svc: CrmDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    lead = await svc.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, detail="Lead not found")

    suggestions = await _generate_lead_suggestions(lead)
    return {"ok": True, "lead_id": lead_id, "suggestions": suggestions}


async def _generate_lead_suggestions(lead: dict[str, Any]) -> list[str]:
    """AI-powered next-action suggestions for a CRM lead. Falls back to rules."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        try:
            return await _openai_lead_suggestions(lead, api_key)
        except Exception as exc:
            log.warning("Lead AI suggestions fallback: %s", exc)
    return _rule_lead_suggestions(lead)


def _rule_lead_suggestions(lead: dict[str, Any]) -> list[str]:
    stage = lead.get("stage", "new")
    score = lead.get("score", 0.0)
    industry = lead.get("industry", "unknown")
    pains = lead.get("pain_points", [])

    mapping = {
        "new": [
            "Send an introductory email referencing their industry pain points.",
            "Research the company's recent news before reaching out.",
            f"Personalise outreach for '{industry}' vertical — highlight relevant case studies.",
        ],
        "qualified": [
            "Schedule a 20-minute discovery call this week.",
            "Share a tailored one-pager or product demo video.",
            "Offer a free audit or pilot scope to lower their commitment threshold.",
        ],
        "proposal": [
            "Follow up within 3 business days if no proposal response.",
            "Offer to walk through the proposal on a live call.",
            "Address any objections raised — check pain points for context.",
        ],
        "negotiation": [
            "Anchor to value, not price — reference ROI metrics.",
            "Prepare a concession plan: what can you offer to close faster?",
            "Set a clear decision deadline with the prospect.",
        ],
        "won": [
            "Send a welcome email with onboarding resources.",
            "Schedule a kickoff call within 48 hours.",
            "Ask for a referral within the first 30 days while value is fresh.",
        ],
        "lost": [
            "Send a short break-up email leaving the door open.",
            "Tag for re-engagement in 3 months.",
            "Document the loss reason for future pipeline coaching.",
        ],
    }

    suggestions = list(mapping.get(stage, mapping["new"]))
    if score < 0.5 and stage in ("new", "qualified"):
        suggestions.insert(0, "Low-score lead — qualify further before investing heavy effort.")
    if pains:
        suggestions.insert(0, f"Pain points detected: {', '.join(pains[:3])}. Lead your messaging with these.")
    return suggestions[:4]


async def _openai_lead_suggestions(lead: dict[str, Any], api_key: str) -> list[str]:
    import httpx

    summary = (
        f"Email: {lead.get('email')}, Company: {lead.get('company', '?')}, "
        f"Industry: {lead.get('industry', '?')}, Stage: {lead.get('stage', 'new')}, "
        f"Score: {int((lead.get('score', 0)) * 100)}%, "
        f"Pain points: {', '.join(lead.get('pain_points', [])) or 'unknown'}"
    )
    prompt = (
        f"You are a B2B sales coach for a South African AI SaaS platform.\n"
        f"Lead profile: {summary}\n\n"
        f"Give 3-4 short, specific, actionable next-step recommendations for this lead. "
        f"Each must be one sentence. Return as a JSON array of strings."
    )

    use_openrouter = not os.environ.get("OPENAI_API_KEY")
    base_url = "https://openrouter.ai/api/v1" if use_openrouter else "https://api.openai.com/v1"
    model = "openai/gpt-4o-mini" if use_openrouter else "gpt-4o-mini"

    async with httpx.AsyncClient(timeout=12) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "max_tokens": 300,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed[:4]
        for key in ("suggestions", "recommendations", "actions", "items"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key][:4]
    return _rule_lead_suggestions(lead)
