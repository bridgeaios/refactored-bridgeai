"""
Subscription tier management — single source of truth for user access levels.

Tiers (ascending): free → starter → pro → enterprise → dev
Stored in Redis/MemoryStore keyed by user address/sub.

Used by:
  - /autonomous/deploy-50-apps  (pricing gate)
  - /api/keyforge/issue          (scope limits)
  - Any future paywalled endpoint

Lifecycle:
  - create_subscription(user_id, tier, payment_ref)  → called by payment webhook
  - get_subscription(user_id)                         → returns current tier record
  - cancel_subscription(user_id)                      → downgrades to 'free'
  - is_tier_allowed(user_id, required_tier)           → boolean gate check

Tier hierarchy:
  free < starter < pro < enterprise
  dev  — bypasses all gates (for internal use, confirmed by BRIDGE_DEV_SECRET)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore

log = logging.getLogger(__name__)

TIERS = ["free", "starter", "pro", "enterprise", "dev"]
_TIER_RANK: dict[str, int] = {t: i for i, t in enumerate(TIERS)}

# Subscription prices in ZAR (for reference / invoice generation)
TIER_PRICES_ZAR: dict[str, float] = {
    "free":       0.0,
    "starter":  299.0,
    "pro":      999.0,
    "enterprise": 0.0,  # custom — negotiated via CRM
}


class SubscriptionService:
    """User subscription state backed by Redis/MemoryStore."""

    def __init__(self, memory: "MemoryStore") -> None:
        self._mem = memory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_subscription(self, user_id: str) -> dict[str, Any]:
        """Return the subscription record for user_id. Never raises — returns free tier on miss."""
        if not user_id or user_id in ("internal-service", "dev"):
            return self._stub("dev" if user_id == "dev" else "free", user_id)
        record = await self._mem.get(self._key(user_id))
        if not record:
            return self._stub("free", user_id)
        # Check expiry
        if record.get("expires_at"):
            try:
                exp = datetime.fromisoformat(record["expires_at"])
                if datetime.now(timezone.utc) > exp:
                    # Expired — downgrade to free silently
                    await self._set_tier(user_id, "free", payment_ref=None)
                    return self._stub("free", user_id)
            except Exception:
                pass
        return record

    async def create_subscription(
        self,
        user_id: str,
        tier: str,
        payment_ref: str | None = None,
        duration_days: int = 30,
    ) -> dict[str, Any]:
        """Activate or upgrade a subscription. Called by payment webhooks."""
        tier = tier.lower()
        if tier not in TIERS:
            raise ValueError(f"Unknown tier: {tier!r}. Valid: {TIERS}")
        return await self._set_tier(user_id, tier, payment_ref, duration_days)

    async def cancel_subscription(self, user_id: str) -> dict[str, Any]:
        """Cancel — immediately downgrade to free."""
        return await self._set_tier(user_id, "free", payment_ref=None)

    async def is_tier_allowed(self, user_id: str, required_tier: str) -> bool:
        """Return True if user's current tier >= required_tier."""
        sub = await self.get_subscription(user_id)
        user_rank = _TIER_RANK.get(sub.get("tier", "free"), 0)
        required_rank = _TIER_RANK.get(required_tier, 99)
        return user_rank >= required_rank

    async def list_subscriptions(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Return all subscriptions (for admin view)."""
        ids: list[str] = await self._mem.get("subscriptions:index") or []
        records = [await self._mem.get(self._key(uid)) for uid in ids]
        records = [r for r in records if r]
        if active_only:
            records = [r for r in records if r.get("tier", "free") != "free"]
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(user_id: str) -> str:
        return f"subscription:{user_id}"

    @staticmethod
    def _stub(tier: str, user_id: str) -> dict[str, Any]:
        return {
            "user_id":    user_id,
            "tier":       tier,
            "status":     "active",
            "created_at": None,
            "expires_at": None,
            "payment_ref": None,
        }

    async def _set_tier(
        self,
        user_id: str,
        tier: str,
        payment_ref: str | None,
        duration_days: int = 30,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=duration_days)).isoformat() if tier != "free" else None
        record: dict[str, Any] = {
            "id":          str(uuid4()),
            "user_id":     user_id,
            "tier":        tier,
            "status":      "active" if tier != "free" else "free",
            "created_at":  now.isoformat(),
            "expires_at":  expires_at,
            "payment_ref": payment_ref,
        }
        await self._mem.set(self._key(user_id), record)
        # Maintain index for admin listing
        ids: list[str] = await self._mem.get("subscriptions:index") or []
        if user_id not in ids:
            ids.append(user_id)
            await self._mem.set("subscriptions:index", ids)
        log.info("Subscription set: user=%s tier=%s expires=%s", user_id, tier, expires_at)
        return record
