"""Email delivery adapter — Resend (primary) or SendGrid (fallback).

Provider is selected by OUTREACH_EMAIL_PROVIDER env var:
  "resend"    → uses RESEND_API_KEY
  "sendgrid"  → uses SENDGRID_API_KEY
  ""          → queue-only mode (logs but does not send)
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

PROVIDER = os.environ.get("OUTREACH_EMAIL_PROVIDER", "").lower().strip()
FROM_EMAIL = os.environ.get("OUTREACH_FROM_EMAIL", "no-reply@ai-os.co.za")
FROM_NAME = os.environ.get("OUTREACH_FROM_NAME", "BridgeAI")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")


async def send_email(
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
) -> dict[str, Any]:
    """Send a single email. Returns {"ok": True, "id": ...} or {"ok": False, "error": ...}."""
    if not PROVIDER:
        log.info("[EMAIL] Queue-only mode — no provider configured. Skipping send to %s", to)
        return {"ok": False, "error": "no_provider", "skipped": True}

    if PROVIDER == "resend":
        return await _send_resend(to, subject, html, text)
    if PROVIDER == "sendgrid":
        return await _send_sendgrid(to, subject, html, text)

    log.warning("[EMAIL] Unknown OUTREACH_EMAIL_PROVIDER=%r — skipping send", PROVIDER)
    return {"ok": False, "error": f"unknown_provider:{PROVIDER}"}


# ---------------------------------------------------------------------------
# Resend
# ---------------------------------------------------------------------------

async def _send_resend(to: str, subject: str, html: str, text: str | None) -> dict[str, Any]:
    if not RESEND_API_KEY:
        log.error("[EMAIL] RESEND_API_KEY not set")
        return {"ok": False, "error": "resend_key_missing"}
    try:
        import httpx
        payload: dict[str, Any] = {
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            )
        if r.status_code in (200, 201):
            data = r.json()
            log.info("[EMAIL] Resend OK → %s id=%s", to, data.get("id"))
            return {"ok": True, "id": data.get("id"), "provider": "resend"}
        log.error("[EMAIL] Resend error %d: %s", r.status_code, r.text[:200])
        return {"ok": False, "error": f"resend_http_{r.status_code}", "detail": r.text[:200]}
    except Exception as exc:
        log.exception("[EMAIL] Resend exception")
        return {"ok": False, "error": type(exc).__name__}


# ---------------------------------------------------------------------------
# SendGrid
# ---------------------------------------------------------------------------

async def _send_sendgrid(to: str, subject: str, html: str, text: str | None) -> dict[str, Any]:
    if not SENDGRID_API_KEY:
        log.error("[EMAIL] SENDGRID_API_KEY not set")
        return {"ok": False, "error": "sendgrid_key_missing"}
    try:
        import httpx
        content = [{"type": "text/html", "value": html}]
        if text:
            content.insert(0, {"type": "text/plain", "value": text})
        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": FROM_EMAIL, "name": FROM_NAME},
            "subject": subject,
            "content": content,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {SENDGRID_API_KEY}"},
            )
        if r.status_code == 202:
            msg_id = r.headers.get("X-Message-Id", "")
            log.info("[EMAIL] SendGrid OK → %s id=%s", to, msg_id)
            return {"ok": True, "id": msg_id, "provider": "sendgrid"}
        log.error("[EMAIL] SendGrid error %d: %s", r.status_code, r.text[:200])
        return {"ok": False, "error": f"sendgrid_http_{r.status_code}", "detail": r.text[:200]}
    except Exception as exc:
        log.exception("[EMAIL] SendGrid exception")
        return {"ok": False, "error": type(exc).__name__}
