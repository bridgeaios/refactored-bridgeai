"""
Discord webhook notifications for key Bridge AI OS events.

Uses Discord Incoming Webhooks — no bot token required, just a webhook URL.
Set DISCORD_WEBHOOK_URL in .env.unified to activate.

Notification events:
  - payment_received   (treasury collect)
  - deal_won           (CRM deal → won)
  - invoice_created    (billing)
  - subscription_activated
  - new_high_score_lead (score >= 0.8)
  - system_error       (5XX rate spike)
  - deploy_complete    (50-app deploy)

Usage:
    from app.services.discord_notify import notify
    await notify("deal_won", {"deal_id": ..., "amount": ..., "client": ...})
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

# Colour codes per event type (Discord embed colour, decimal)
_COLOURS = {
    "payment_received":        0x00C851,  # green
    "deal_won":                0x6C47FF,  # brand purple
    "invoice_created":         0x33B5E5,  # blue
    "subscription_activated":  0xFF8800,  # orange
    "new_high_score_lead":     0xFFBB33,  # amber
    "system_error":            0xFF4444,  # red
    "deploy_complete":         0x00C851,  # green
    "ubi_disbursed":           0x2BBBAD,  # teal
}

_TITLES = {
    "payment_received":        "Payment Received",
    "deal_won":                "Deal Won",
    "invoice_created":         "Invoice Created",
    "subscription_activated":  "Subscription Activated",
    "new_high_score_lead":     "Hot Lead Detected",
    "system_error":            "System Error Alert",
    "deploy_complete":         "Autonomous Deploy Complete",
    "ubi_disbursed":           "UBI Disbursement",
}


async def notify(event: str, data: dict[str, Any], webhook_url: str | None = None) -> bool:
    """
    Send a Discord embed notification for the given event.
    Returns True on success, False on failure or if webhook not configured.
    """
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return False

    colour = _COLOURS.get(event, 0x888888)
    title  = _TITLES.get(event, event.replace("_", " ").title())

    fields = [
        {"name": k.replace("_", " ").title(), "value": str(v)[:1024], "inline": True}
        for k, v in data.items()
        if v is not None and str(v).strip()
    ]

    payload = {
        "embeds": [{
            "title":       title,
            "color":       colour,
            "fields":      fields[:25],  # Discord max
            "footer":      {"text": "Bridge AI OS"},
            "timestamp":   _utcnow(),
        }]
    }

    try:
        import httpx
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post(url, json=payload)
            if r.status_code in (200, 204):
                return True
            log.warning("Discord notify HTTP %s for event '%s'", r.status_code, event)
            return False
    except Exception as exc:
        log.debug("Discord notify failed for '%s': %s", event, exc)
        return False


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
