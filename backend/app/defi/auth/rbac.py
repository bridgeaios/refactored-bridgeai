"""
RBAC — tier-based limits, fees, and rate limiting.

Tiers: Basic → Silver → Gold → Platinum
Upgrade: auto-upgrade when 30-day rolling volume crosses threshold.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.defi.auth.jwt_manager import decode_access_token
from app.defi.database import get_db
from app.defi.models import DefiUser, Tier

# Module-level dependency singleton for get_db
_db_dep = Depends(get_db)


# ---------------------------------------------------------------------------
# Tier configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TierConfig:
    tier: Tier
    daily_limit_usd: float   # -1 = unlimited
    fee_pct: float            # 0.5 = 0.5%
    rate_limit_per_min: int  # -1 = unlimited
    upgrade_volume_usd: float  # 30-day rolling volume to auto-upgrade


TIER_CONFIG: dict[Tier, TierConfig] = {
    Tier.BASIC:    TierConfig(Tier.BASIC,    1_000.0,   0.50, 60,   10_000.0),
    Tier.SILVER:   TierConfig(Tier.SILVER,  10_000.0,   0.40, 120,  50_000.0),
    Tier.GOLD:     TierConfig(Tier.GOLD,    50_000.0,   0.25, 300, 200_000.0),
    Tier.PLATINUM: TierConfig(Tier.PLATINUM,    -1.0,   0.10,  -1,       -1.0),
}

# Tier order for comparisons
_TIER_ORDER = [Tier.BASIC, Tier.SILVER, Tier.GOLD, Tier.PLATINUM]


def tier_gte(a: Tier, b: Tier) -> bool:
    """Return True if tier a >= b."""
    return _TIER_ORDER.index(a) >= _TIER_ORDER.index(b)


def effective_fee_pct(tier: Tier, native_token_holdings: float) -> float:
    """Fee with 5% reduction if user holds native token (BRDG)."""
    base = TIER_CONFIG[tier].fee_pct
    if native_token_holdings > 0:
        return round(base * 0.95, 4)  # 5% discount
    return base


def auto_upgrade_tier(current: Tier, volume_30d_usd: float) -> Tier:
    """Return upgraded tier if volume threshold crossed."""
    upgraded = current
    for tier in _TIER_ORDER:
        cfg = TIER_CONFIG[tier]
        if cfg.upgrade_volume_usd > 0 and volume_30d_usd >= cfg.upgrade_volume_usd:
            upgraded = tier
    return upgraded


def subscription_discount_pct(billing_cycle: str) -> float:
    """Return discount fraction: 0.10 for semi-annual, 0.20 for annual."""
    if billing_cycle == "semi_annual":
        return 0.10
    if billing_cycle == "annual":
        return 0.20
    return 0.0


# ---------------------------------------------------------------------------
# FastAPI dependency — current user
# ---------------------------------------------------------------------------
async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = _db_dep,
) -> DefiUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired") from err
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = int(payload["sub"])
    result = await db.execute(select(DefiUser).where(DefiUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found or inactive")
    return user


# Module-level dependency singleton for get_current_user (after function definition)
_user_dep = Depends(get_current_user)


def require_tier(minimum: Tier):
    """Dependency factory — raise 403 if user's tier is below minimum."""
    async def _check(user: DefiUser = _user_dep) -> DefiUser:
        if not tier_gte(user.tier, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires {minimum.value} tier or higher",
            )
        return user
    return _check
