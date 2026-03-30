"""CRM domain router — leads, pipeline, deals."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.domains.crm.deps import get_crm
from app.domains.crm.models import DealCreate, LeadIngest, NoteCreate, StageUpdate
from app.domains.crm.services import CrmService
from app.domains.infra.deps import require_jwt

router = APIRouter(tags=["crm"])

CrmDep = Annotated[CrmService, Depends(get_crm)]


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
    _: dict = Depends(require_jwt),
    invoice_id: str | None = None,
) -> dict[str, Any]:
    deal = await svc.mark_deal_won(deal_id, invoice_id)
    if not deal:
        raise HTTPException(404, detail="Deal not found")
    return {"ok": True, "deal": deal}
