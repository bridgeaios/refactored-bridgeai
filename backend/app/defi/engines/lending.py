"""
Lending engine — pure math, no I/O.

Compound interest: A = P(1 + r/n)^(n*t)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class LoanTerms:
    principal_usd: float
    collateral_required_usd: float
    collateral_amount: float
    collateral_token: str
    interest_rate_annual: float   # e.g. 0.12 = 12%
    origination_fee_usd: float
    origination_fee_pct: float
    daily_interest_usd: float
    total_repayable_usd: float    # principal + 30-day interest + fee
    liquidation_threshold: float  # 1.10 = 110%
    liquidation_bonus: float      # 0.05 = 5%


# Tiered interest rates (p.a.)
_INTEREST_RATES = {
    "basic":    0.15,
    "silver":   0.13,
    "gold":     0.10,
    "platinum": 0.07,
}

# Origination fee per tier
_ORIGINATION_FEES = {
    "basic":    0.020,   # 2%
    "silver":   0.015,
    "gold":     0.010,
    "platinum": 0.005,
}

_COLLATERAL_PRICES_USD: dict[str, float] = {
    "ETH": 3200.0,
    "BTC": 62000.0,
    "SOL": 180.0,
    "USDC": 1.0,
    "USDT": 1.0,
    "BRDG": 0.10,
}


def get_collateral_price(token: str) -> float:
    return _COLLATERAL_PRICES_USD.get(token.upper(), 1.0)


def calculate_loan_terms(
    principal_usd: float,
    collateral_token: str,
    collateral_ratio: float,
    duration_days: int,
    tier: str,
) -> LoanTerms:
    rate = _INTEREST_RATES.get(tier, 0.15)
    fee_pct = _ORIGINATION_FEES.get(tier, 0.02)
    origination_fee = round(principal_usd * fee_pct, 4)

    collateral_usd = round(principal_usd * collateral_ratio, 4)
    token_price = get_collateral_price(collateral_token)
    collateral_amount = round(collateral_usd / token_price, 6)

    # Compound daily interest for duration_days
    n = 365  # compound frequency
    t = duration_days / 365
    accrued = principal_usd * ((1 + rate / n) ** (n * t) - 1)
    daily = principal_usd * ((1 + rate / n) ** (n / 365) - 1)
    total_repayable = round(principal_usd + accrued + origination_fee, 4)

    return LoanTerms(
        principal_usd=principal_usd,
        collateral_required_usd=collateral_usd,
        collateral_amount=collateral_amount,
        collateral_token=collateral_token.upper(),
        interest_rate_annual=rate,
        origination_fee_usd=origination_fee,
        origination_fee_pct=fee_pct,
        daily_interest_usd=round(daily, 4),
        total_repayable_usd=total_repayable,
        liquidation_threshold=1.10,
        liquidation_bonus=0.05,
    )


def compound_interest(
    principal: float,
    rate_annual: float,
    frequency: int,
    elapsed_seconds: float,
) -> float:
    """Return accrued interest (not including principal)."""
    t = elapsed_seconds / 86400 / 365  # fractional years
    n = frequency
    return principal * ((1 + rate_annual / n) ** (n * t) - 1)


def health_factor(collateral_usd: float, outstanding_usd: float, threshold: float = 1.10) -> float:
    """
    Health factor = collateral_usd / (outstanding_usd * threshold).
    < 1.0 → liquidatable.
    """
    if outstanding_usd <= 0:
        return float("inf")
    return collateral_usd / (outstanding_usd * threshold)


def is_liquidatable(collateral_usd: float, outstanding_usd: float, threshold: float = 1.10) -> bool:
    return health_factor(collateral_usd, outstanding_usd, threshold) < 1.0


def liquidation_proceeds(collateral_usd: float, bonus: float = 0.05) -> float:
    """Amount liquidator receives (collateral + bonus)."""
    return round(collateral_usd * (1 + bonus), 4)
