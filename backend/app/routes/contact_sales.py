"""
Contact Sales endpoint — Human-in-the-Loop (HITL) sales inquiry handler.

Flow:
  1. Enterprise visitor fills out the contact form on pricing.html
  2. POST /api/contact-sales receives the inquiry (no auth required)
  3. Email dispatched to ADMIN_EMAIL — the brain/kernel/human inbox
  4. Human (twin operator) reviews and replies — no auto-reply is sent to prospect

Email priority: Resend (if RESEND_API_KEY set) → SMTP/Brevo fallback.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr

log = logging.getLogger(__name__)

router = APIRouter(tags=["contact"])

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "ryanpcowan@gmail.com")
SMTP_FROM = os.environ.get("SMTP_FROM", "admin@ai-os.co.za")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Bridge AI OS")


class ContactSalesPayload(BaseModel):
    name: str
    email: EmailStr
    company: str = ""
    message: str = ""


@router.post("/contact-sales")
async def contact_sales(payload: ContactSalesPayload, request: Request) -> dict[str, Any]:
    """Public endpoint — no auth. Routes enterprise inquiry to the human brain/kernel inbox."""
    ip = request.client.host if request.client else "unknown"
    log.info("[CONTACT-SALES] inquiry from %s <%s> company=%r ip=%s",
             payload.name, payload.email, payload.company, ip)

    subject = f"[Sales Inquiry] {payload.company or payload.name} — Bridge AI OS"
    result = await _send_to_brain(
        subject=subject,
        html=_html(payload, ip),
        text=_text(payload, ip),
    )
    if not result["ok"]:
        log.warning("[CONTACT-SALES] email delivery issue: %s — inquiry logged", result.get("error"))

    return {"ok": True, "message": "Thank you! We'll be in touch within 24 hours."}


# ---------------------------------------------------------------------------
# Delivery — Resend primary, SMTP (Brevo) fallback
# ---------------------------------------------------------------------------

async def _send_to_brain(subject: str, html: str, text: str) -> dict[str, Any]:
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if resend_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}"},
                    json={
                        "from": f"{SMTP_FROM_NAME} <{SMTP_FROM}>",
                        "to": [ADMIN_EMAIL],
                        "subject": subject,
                        "html": html,
                        "text": text,
                    },
                )
            if r.status_code in (200, 201):
                log.info("[CONTACT-SALES] Resend OK → %s", ADMIN_EMAIL)
                return {"ok": True, "provider": "resend"}
            log.warning("[CONTACT-SALES] Resend %d — falling back to SMTP", r.status_code)
        except Exception as exc:
            log.warning("[CONTACT-SALES] Resend exception: %s — trying SMTP", exc)

    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    if smtp_host and smtp_user:
        try:
            import aiosmtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
            msg["To"] = ADMIN_EMAIL
            msg["Reply-To"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            await aiosmtplib.send(
                msg,
                hostname=smtp_host,
                port=int(os.environ.get("SMTP_PORT", "587")),
                username=smtp_user,
                password=smtp_pass,
                start_tls=True,
            )
            log.info("[CONTACT-SALES] SMTP OK → %s", ADMIN_EMAIL)
            return {"ok": True, "provider": "smtp"}
        except Exception as exc:
            log.exception("[CONTACT-SALES] SMTP failed")
            return {"ok": False, "error": str(exc)}

    log.warning("[CONTACT-SALES] no email provider configured — inquiry logged only")
    return {"ok": False, "error": "no_provider"}


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

def _html(p: ContactSalesPayload, ip: str) -> str:
    company_row = f'<tr><td style="padding:8px 0;color:#94a3b8;font-size:13px;width:110px;">Company</td><td style="padding:8px 0;">{p.company}</td></tr>' if p.company else ""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="background:#060810;color:#fff;font-family:Arial,sans-serif;padding:30px;max-width:600px;margin:0 auto;">
  <div style="border:1px solid #1a2a3a;border-radius:12px;padding:30px;background:#0a0e17;">
    <p style="color:#63ffda;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 8px;">Bridge AI OS · Human-in-the-Loop</p>
    <h1 style="color:#fff;margin:0 0 6px;font-size:22px;">New Enterprise Sales Inquiry</h1>
    <p style="color:#94a3b8;font-size:13px;margin:0 0 20px;">Review below and reply directly to the prospect — no auto-reply has been sent.</p>
    <hr style="border:none;border-top:1px solid #1a2a3a;margin:0 0 20px;">
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:8px 0;color:#94a3b8;font-size:13px;width:110px;">Name</td><td style="padding:8px 0;font-weight:600;">{p.name}</td></tr>
      <tr><td style="padding:8px 0;color:#94a3b8;font-size:13px;">Email</td><td style="padding:8px 0;"><a href="mailto:{p.email}" style="color:#63ffda;text-decoration:none;">{p.email}</a></td></tr>
      {company_row}
    </table>
    <hr style="border:none;border-top:1px solid #1a2a3a;margin:20px 0;">
    <p style="color:#63ffda;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 10px;">Message</p>
    <p style="color:#e2e8f0;line-height:1.7;background:#111827;padding:16px;border-radius:8px;border-left:3px solid #63ffda;margin:0;">{p.message or "(no message provided)"}</p>
    <hr style="border:none;border-top:1px solid #1a2a3a;margin:20px 0;">
    <a href="mailto:{p.email}?subject=Re: Your Bridge AI OS Enterprise Inquiry" style="display:inline-block;background:#63ffda;color:#000;padding:12px 28px;border-radius:6px;font-weight:700;text-decoration:none;font-size:14px;">Reply to {p.name}</a>
    <p style="color:#475569;font-size:11px;margin:16px 0 0;">Source IP: {ip}</p>
  </div>
</body></html>"""


def _text(p: ContactSalesPayload, ip: str) -> str:
    return (
        "NEW ENTERPRISE SALES INQUIRY — Bridge AI OS\n"
        "============================================\n\n"
        f"Name:    {p.name}\n"
        f"Email:   {p.email}\n"
        f"Company: {p.company or '—'}\n\n"
        "Message:\n"
        f"{p.message or '(no message provided)'}\n\n"
        "----\n"
        f"Source IP: {ip}\n"
        "No auto-reply has been sent — human review required.\n"
        f"Reply directly: {p.email}\n"
    )
