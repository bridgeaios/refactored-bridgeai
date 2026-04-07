"""Compliance domain service — legal docs storage and AI suggestions."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore

log = logging.getLogger(__name__)

_DOCS_KEY = "compliance:docs"
_DOCS_TYPE_LABELS = {
    "nda": "NDA",
    "msa": "Master Service Agreement",
    "privacy_policy": "Privacy Policy",
    "terms_of_service": "Terms of Service",
    "sla": "SLA",
    "data_processing": "Data Processing Agreement",
    "gdpr_consent": "GDPR Consent Form",
    "other": "Other",
}

# Rule-based suggestions per doc-type gap
_DOC_SUGGESTIONS: dict[str, str] = {
    "nda": "Add a Non-Disclosure Agreement to protect IP when sharing sensitive project details with this contact.",
    "msa": "A Master Service Agreement would standardise engagement terms and reduce per-project negotiation overhead.",
    "privacy_policy": "Ensure a signed Privacy Policy acknowledgement is on file before processing personal data.",
    "sla": "Define SLA metrics (uptime, response time) upfront to prevent disputes later.",
    "data_processing": "If processing EU data, a Data Processing Agreement (GDPR Art. 28) is mandatory.",
    "gdpr_consent": "Capture explicit GDPR consent before adding this contact to marketing workflows.",
    "terms_of_service": "Link your Terms of Service to the deal so clients accept scope and liability clauses.",
}


def _store_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    d = repo_root / ".bridge-state" / "compliance_docs"
    d.mkdir(parents=True, exist_ok=True)
    return d


class ComplianceService:
    def __init__(self, memory: MemoryStore) -> None:
        self._mem = memory

    # ------------------------------------------------------------------ #
    # Doc CRUD                                                             #
    # ------------------------------------------------------------------ #

    async def list_docs(self, contact_id: str = "") -> list[dict[str, Any]]:
        docs: list[dict] = await self._mem.get(_DOCS_KEY) or []
        if contact_id:
            docs = [d for d in docs if d.get("contact_id") == contact_id]
        return docs

    async def save_doc(
        self,
        filename: str,
        content: bytes,
        doc_type: str,
        notes: str,
        contact_id: str,
        uploader: str,
    ) -> dict[str, Any]:
        doc_id = str(uuid4())
        dest = _store_dir() / doc_id
        dest.write_bytes(content)

        record: dict[str, Any] = {
            "id": doc_id,
            "name": filename,
            "doc_type": doc_type,
            "filename": filename,
            "size_bytes": len(content),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "uploader": uploader,
            "contact_id": contact_id,
            "notes": notes,
        }
        docs: list[dict] = await self._mem.get(_DOCS_KEY) or []
        docs.append(record)
        await self._mem.set(_DOCS_KEY, docs)
        return record

    async def get_doc_bytes(self, doc_id: str) -> tuple[bytes, str] | None:
        docs: list[dict] = await self._mem.get(_DOCS_KEY) or []
        record = next((d for d in docs if d["id"] == doc_id), None)
        if not record:
            return None
        dest = _store_dir() / doc_id
        if not dest.exists():
            return None
        return dest.read_bytes(), record["filename"]

    async def delete_doc(self, doc_id: str) -> bool:
        docs: list[dict] = await self._mem.get(_DOCS_KEY) or []
        new_docs = [d for d in docs if d["id"] != doc_id]
        if len(new_docs) == len(docs):
            return False
        await self._mem.set(_DOCS_KEY, new_docs)
        dest = _store_dir() / doc_id
        if dest.exists():
            dest.unlink()
        return True

    # ------------------------------------------------------------------ #
    # AI suggestions                                                       #
    # ------------------------------------------------------------------ #

    async def ai_suggestions(
        self,
        contact: dict[str, Any] | None,
        existing_doc_types: list[str],
        extra_context: str = "",
    ) -> list[str]:
        """Return AI-generated compliance recommendations.

        Tries OpenAI first; falls back to rule-based suggestions on any error.
        """
        rule_based = self._rule_suggestions(contact, existing_doc_types)
        try:
            return await self._openai_suggestions(contact, existing_doc_types, extra_context, rule_based)
        except Exception as exc:
            log.warning("AI suggestions fallback to rules: %s", exc)
            return rule_based

    def _rule_suggestions(
        self,
        contact: dict[str, Any] | None,
        existing_doc_types: list[str],
    ) -> list[str]:
        suggestions: list[str] = []
        missing = set(_DOC_SUGGESTIONS.keys()) - set(existing_doc_types)
        # Prioritise based on contact industry
        industry = (contact or {}).get("industry", "unknown")
        priority: list[str] = []
        if industry in ("tech", "consulting", "marketing"):
            priority = ["nda", "msa", "sla"]
        elif industry in ("finance", "legal"):
            priority = ["data_processing", "gdpr_consent", "nda"]
        elif industry == "ecommerce":
            priority = ["privacy_policy", "terms_of_service", "gdpr_consent"]
        else:
            priority = list(_DOC_SUGGESTIONS.keys())

        for key in priority:
            if key in missing:
                suggestions.append(_DOC_SUGGESTIONS[key])
        return suggestions[:5]

    async def _openai_suggestions(
        self,
        contact: dict[str, Any] | None,
        existing_doc_types: list[str],
        extra_context: str,
        fallback: list[str],
    ) -> list[str]:
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return fallback

        import httpx

        contact_summary = ""
        if contact:
            contact_summary = (
                f"Company: {contact.get('company', 'unknown')}, "
                f"Industry: {contact.get('industry', 'unknown')}, "
                f"Stage: {contact.get('stage', 'new')}, "
                f"Score: {int((contact.get('score', 0)) * 100)}%"
            )

        docs_on_file = ", ".join(existing_doc_types) or "none"
        prompt = (
            f"You are a legal compliance advisor for a B2B SaaS platform in South Africa.\n"
            f"Contact info: {contact_summary or 'No contact data.'}\n"
            f"Legal docs already on file: {docs_on_file}\n"
            f"Additional context: {extra_context or 'None'}\n\n"
            f"Provide 3-5 concise, actionable compliance recommendations. "
            f"Each recommendation should be one sentence. Return as a JSON array of strings."
        )

        use_openrouter = not os.environ.get("OPENAI_API_KEY")
        base_url = "https://openrouter.ai/api/v1" if use_openrouter else "https://api.openai.com/v1"
        model = "openai/gpt-4o-mini" if use_openrouter else "gpt-4o-mini"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 400,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            import json
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            # Accept {"suggestions": [...]} or direct array wrapper keys
            if isinstance(parsed, list):
                return parsed[:5]
            for key in ("suggestions", "recommendations", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key][:5]
            return fallback
