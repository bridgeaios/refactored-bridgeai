"""CRM domain service — lead ingestion, scoring, pipeline management."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore

log = logging.getLogger(__name__)

# Pipeline stages in order
STAGES = ["new", "qualified", "proposal", "negotiation", "won", "lost"]

# Industry scoring weights — how well each industry fits the platform
_INDUSTRY_FIT: dict[str, float] = {
    "tech": 1.0, "marketing": 0.9, "finance": 0.85,
    "consulting": 0.8, "ecommerce": 0.75, "real_estate": 0.7,
    "legal": 0.65, "healthcare": 0.6, "construction": 0.5,
    "manufacturing": 0.5, "unknown": 0.4,
}


def _score_lead(osint: dict[str, Any]) -> float:
    """Score 0.0–1.0 from OSINT profile signals."""
    confidence = float(osint.get("profile_confidence", 0.0))
    industry = osint.get("industry", "unknown")
    size = osint.get("size_estimate", "unknown")
    email_domain = osint.get("email_domain", "")

    industry_fit = _INDUSTRY_FIT.get(industry, 0.4)

    size_weight = {"startup": 0.6, "small": 0.7, "medium": 0.85,
                   "large": 0.9, "enterprise": 1.0, "unknown": 0.4}.get(size, 0.4)

    domain_quality = 0.8 if (email_domain and email_domain not in
                              {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}) else 0.4

    score = (confidence * 0.35) + (industry_fit * 0.30) + (size_weight * 0.20) + (domain_quality * 0.15)
    return round(min(max(score, 0.0), 1.0), 3)


def _auto_stage(score: float) -> str:
    """Automatically advance high-confidence leads past 'new'."""
    if score >= 0.7:
        return "qualified"
    return "new"


class CrmService:
    """In-memory CRM backed by Redis/MemoryStore.
    Migrate to PostgreSQL via SQLAlchemy when DATABASE_DEFI_URL is set to Neon.
    """

    def __init__(self, memory: MemoryStore) -> None:
        self._mem = memory

    # ------------------------------------------------------------------
    # Outreach email templates per pipeline stage
    # ------------------------------------------------------------------

    # Maps each CRM stage to: (email subject template, body template)
    _STAGE_EMAILS: dict[str, tuple[str, str]] = {
        "qualified": (
            "You've been shortlisted for the Bridge AI OS pilot",
            "Hi {name},\n\nWe reviewed your profile and you're a great fit for our AI platform pilot.\n\n"
            "We'd love to schedule a quick call to show you what's possible.\n\n"
            "Reply to this email or book directly: https://bridge-ai-os.com/join\n\nBridge AI OS Team",
        ),
        "proposal": (
            "Your Bridge AI OS proposal is ready",
            "Hi {name},\n\nYour custom proposal for {company} is ready to view.\n\n"
            "We've tailored a deployment plan based on your industry and requirements.\n\n"
            "Review proposal: https://bridge-ai-os.com/dashboard\n\nBridge AI OS Team",
        ),
        "negotiation": (
            "Let's finalise your Bridge AI OS agreement",
            "Hi {name},\n\nWe're excited to move forward with {company}.\n\n"
            "Our team is ready to finalise terms. What time works for a brief call?\n\n"
            "Schedule: https://bridge-ai-os.com/join\n\nBridge AI OS Team",
        ),
        "won": (
            "Welcome to Bridge AI OS — you're in!",
            "Hi {name},\n\nCongratulations! {company} is now an active Bridge AI OS client.\n\n"
            "Your dashboard is live: https://bridge-ai-os.com/dashboard\n\n"
            "Your onboarding specialist will reach out within 24 hours.\n\nBridge AI OS Team",
        ),
        "lost": (
            "Keeping the door open — Bridge AI OS",
            "Hi {name},\n\nWe understand the timing may not be right.\n\n"
            "If anything changes, we'd love to reconnect. Our platform continues to evolve rapidly.\n\n"
            "https://bridge-ai-os.com\n\nBridge AI OS Team",
        ),
    }

    # ------------------------------------------------------------------
    # Lead CRUD
    # ------------------------------------------------------------------

    async def ingest_lead(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Ingest a lead from the scraper. Returns existing record if duplicate."""
        email = (payload.get("email") or "").strip().lower()
        if not email:
            raise ValueError("email is required")

        # Dedup by email
        existing_id = await self._mem.get(f"crm:email:{email}")
        if existing_id:
            existing = await self._mem.get(f"crm:lead:{existing_id}")
            if existing:
                return {**existing, "duplicate": True}

        osint = payload.get("osint_profile") or {}
        if not isinstance(osint, dict):
            osint = {}

        score = _score_lead(osint)
        stage = _auto_stage(score)
        now = datetime.now(timezone.utc).isoformat()
        lead_id = str(uuid4())

        lead: dict[str, Any] = {
            "id": lead_id,
            "email": email,
            "company": payload.get("company", ""),
            "name": payload.get("name", ""),
            "phone": payload.get("phone", ""),
            "source": payload.get("source", "scraper"),
            "stage": stage,
            "score": score,
            "industry": osint.get("industry", "unknown"),
            "size_estimate": osint.get("size_estimate", "unknown"),
            "email_domain": osint.get("email_domain", ""),
            "pain_points": osint.get("pain_points", []),
            "template_type": osint.get("template_type", "generic"),
            "decision_makers": osint.get("decision_makers", []),
            "osint_profile": osint,
            "created_at": now,
            "updated_at": now,
            "activities": [],
            "deal_id": None,
        }

        await self._mem.set(f"crm:lead:{lead_id}", lead)
        await self._mem.set(f"crm:email:{email}", lead_id)

        # Append to index
        ids: list = await self._mem.get("crm:leads:index") or []
        ids.append(lead_id)
        await self._mem.set("crm:leads:index", ids)

        log.info("CRM lead ingested id=%s email=%s stage=%s score=%.3f", lead_id, email, stage, score)
        return {**lead, "duplicate": False}

    async def get_lead(self, lead_id: str) -> dict[str, Any] | None:
        return await self._mem.get(f"crm:lead:{lead_id}")

    async def list_leads(
        self,
        stage: str | None = None,
        source: str | None = None,
        min_score: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ids: list = await self._mem.get("crm:leads:index") or []
        leads = [await self._mem.get(f"crm:lead:{i}") for i in ids]
        leads = [l for l in leads if l]

        if stage:
            leads = [l for l in leads if l.get("stage") == stage]
        if source:
            leads = [l for l in leads if l.get("source") == source]
        if min_score is not None:
            leads = [l for l in leads if l.get("score", 0) >= min_score]

        leads.sort(key=lambda x: x.get("score", 0), reverse=True)
        return leads[offset: offset + limit]

    async def update_stage(self, lead_id: str, stage: str, note: str = "") -> dict[str, Any] | None:
        lead = await self._mem.get(f"crm:lead:{lead_id}")
        if not lead:
            return None
        prev_stage = lead.get("stage", "new")
        lead["stage"] = stage
        lead["updated_at"] = datetime.now(timezone.utc).isoformat()
        if note:
            lead.setdefault("activities", []).append(
                {"type": "stage_change", "text": f"→ {stage}: {note}",
                 "created_at": lead["updated_at"]}
            )
        await self._mem.set(f"crm:lead:{lead_id}", lead)

        # Queue outreach email when stage advances to a key milestone
        if stage != prev_stage and stage in self._STAGE_EMAILS:
            await self._queue_stage_email(lead, stage)

        return lead

    async def _queue_stage_email(self, lead: dict[str, Any], stage: str) -> None:
        """Enqueue a personalised outreach email for the new pipeline stage."""
        template = self._STAGE_EMAILS.get(stage)
        if not template:
            return
        subject_tmpl, body_tmpl = template
        name    = (lead.get("first_name") or lead.get("name") or "there").strip()
        company = (lead.get("company") or "your company").strip()
        email   = lead.get("email", "")
        if not email:
            return
        try:
            from app.services.outreach import enqueue_outreach
            await enqueue_outreach(self._mem, {
                "to":      email,
                "name":    name,
                "subject": subject_tmpl,
                "body":    body_tmpl.format(name=name, company=company),
                "source":  f"crm_stage_{stage}",
                "lead_id": lead.get("id"),
            })
            log.info("Outreach queued for lead %s → stage '%s'", lead.get("id"), stage)
        except Exception as exc:
            log.warning("Outreach queue failed for lead %s: %s", lead.get("id"), exc)

    async def add_note(self, lead_id: str, text: str) -> dict[str, Any] | None:
        lead = await self._mem.get(f"crm:lead:{lead_id}")
        if not lead:
            return None
        now = datetime.now(timezone.utc).isoformat()
        lead.setdefault("activities", []).append(
            {"type": "note", "text": text, "created_at": now}
        )
        lead["updated_at"] = now
        await self._mem.set(f"crm:lead:{lead_id}", lead)
        return lead

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    async def pipeline(self) -> dict[str, Any]:
        ids: list = await self._mem.get("crm:leads:index") or []
        leads = [await self._mem.get(f"crm:lead:{i}") for i in ids]
        leads = [l for l in leads if l]

        by_stage: dict[str, list] = {s: [] for s in STAGES}
        for lead in leads:
            stage = lead.get("stage", "new")
            if stage in by_stage:
                by_stage[stage].append(lead)

        stages = []
        total_value = 0.0
        for stage_name in STAGES:
            items = by_stage[stage_name]
            value = sum(l.get("deal_value", 0.0) for l in items)
            total_value += value
            stages.append({"name": stage_name, "count": len(items),
                           "total_value": value, "leads": items})

        return {"stages": stages, "total_leads": len(leads), "total_value": total_value}

    async def stats(self) -> dict[str, Any]:
        ids: list = await self._mem.get("crm:leads:index") or []
        leads = [await self._mem.get(f"crm:lead:{i}") for i in ids]
        leads = [l for l in leads if l]

        if not leads:
            return {"total_leads": 0, "by_stage": {}, "by_source": {},
                    "by_industry": {}, "avg_score": 0.0, "conversion_rate": 0.0}

        by_stage: dict[str, int] = {}
        by_source: dict[str, int] = {}
        by_industry: dict[str, int] = {}
        total_score = 0.0

        for l in leads:
            by_stage[l.get("stage", "new")] = by_stage.get(l.get("stage", "new"), 0) + 1
            by_source[l.get("source", "unknown")] = by_source.get(l.get("source", "unknown"), 0) + 1
            by_industry[l.get("industry", "unknown")] = by_industry.get(l.get("industry", "unknown"), 0) + 1
            total_score += l.get("score", 0.0)

        won = by_stage.get("won", 0)
        conversion = round(won / len(leads), 3) if leads else 0.0

        return {
            "total_leads": len(leads),
            "by_stage": by_stage,
            "by_source": by_source,
            "by_industry": by_industry,
            "avg_score": round(total_score / len(leads), 3),
            "conversion_rate": conversion,
        }

    # ------------------------------------------------------------------
    # Deals
    # ------------------------------------------------------------------

    async def create_deal(self, lead_id: str, title: str, value: float, currency: str = "ZAR") -> dict[str, Any] | None:
        lead = await self._mem.get(f"crm:lead:{lead_id}")
        if not lead:
            return None
        now = datetime.now(timezone.utc).isoformat()
        deal_id = str(uuid4())
        deal = {
            "id": deal_id, "lead_id": lead_id, "title": title,
            "value": value, "currency": currency, "stage": "open",
            "invoice_id": None, "created_at": now, "closed_at": None,
        }
        await self._mem.set(f"crm:deal:{deal_id}", deal)
        lead["deal_id"] = deal_id
        lead["deal_value"] = value
        lead["updated_at"] = now
        await self._mem.set(f"crm:lead:{lead_id}", lead)
        return deal

    async def get_deal(self, deal_id: str) -> dict[str, Any] | None:
        return await self._mem.get(f"crm:deal:{deal_id}")

    async def mark_deal_won(self, deal_id: str, invoice_id: str | None = None) -> dict[str, Any] | None:
        deal = await self._mem.get(f"crm:deal:{deal_id}")
        if not deal:
            return None
        deal["stage"] = "won"
        deal["closed_at"] = datetime.now(timezone.utc).isoformat()
        if invoice_id:
            deal["invoice_id"] = invoice_id
        await self._mem.set(f"crm:deal:{deal_id}", deal)
        # also update lead stage
        await self.update_stage(deal["lead_id"], "won")
        return deal
