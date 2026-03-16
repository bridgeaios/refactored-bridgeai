"""
Pydantic v2 DTOs for DeFi API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.defi.models import (
    LoanStatus,
    StakeStatus,
    SubscriptionPlan,
    SubscriptionStatus,
    Tier,
    YieldStatus,
)


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------
class OkResponse(BaseModel):
    ok: bool = True


class ErrorResponse(BaseModel):
    ok: bool = False
    detail: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class GoogleOAuthRequest(BaseModel):
    code: str
    redirect_uri: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 min


class RefreshRequest(BaseModel):
    refresh_token: str


class RevokeRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: int
    email: EmailStr
    name: str | None = None
    picture: str | None = None
    tier: Tier
    native_token_holdings: float
    voucher_credits: float
    total_volume_usd: float
    geo_country: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------
class SubscriptionCreate(BaseModel):
    plan: SubscriptionPlan
    billing_cycle: str = Field("monthly", pattern="^(monthly|semi_annual|annual)$")
    payment_rail: str = "paystack"
    voucher_code: str | None = None


class SubscriptionOut(BaseModel):
    id: int
    plan: SubscriptionPlan
    status: SubscriptionStatus
    billing_cycle: str
    price_usd: float
    discount_pct: float
    started_at: datetime
    next_billing_at: datetime | None = None

    class Config:
        from_attributes = True


class PricingPreview(BaseModel):
    plan: SubscriptionPlan
    billing_cycle: str
    base_price_usd: float
    discount_pct: float
    final_price_usd: float
    native_token_discount_pct: float
    final_with_token_usd: float


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------
class LoanQuote(BaseModel):
    principal_usd: float = Field(gt=0)
    collateral_token: str = "ETH"
    duration_days: int = Field(30, ge=1, le=365)
    desired_collateral_ratio: float = Field(1.5, ge=1.1, le=2.0)


class LoanQuoteResponse(BaseModel):
    principal_usd: float
    collateral_required_usd: float
    collateral_amount: float
    collateral_token: str
    interest_rate_annual: float
    origination_fee_usd: float
    total_repayable_usd: float
    daily_interest_usd: float
    fee_pct: float
    tier: Tier


class LoanCreate(BaseModel):
    principal_usd: float = Field(gt=0)
    collateral_token: str = "ETH"
    collateral_amount: float = Field(gt=0)
    duration_days: int = Field(30, ge=1, le=365)
    desired_collateral_ratio: float = Field(1.5, ge=1.1, le=2.0)


class LoanOut(BaseModel):
    id: int
    principal_usd: float
    outstanding_principal: float
    accrued_interest: float
    collateral_usd: float
    collateral_amount: float
    collateral_token: str
    collateral_ratio: float
    interest_rate_annual: float
    status: LoanStatus
    duration_days: int
    opened_at: datetime
    due_at: datetime | None = None
    health_factor: float

    class Config:
        from_attributes = True


class LoanRepayRequest(BaseModel):
    amount_usd: float = Field(gt=0)
    tx_hash: str | None = None


# ---------------------------------------------------------------------------
# Staking
# ---------------------------------------------------------------------------
STAKE_APY: dict[int, float] = {
    30:  0.06,   # 6% p.a.
    60:  0.09,   # 9%
    90:  0.12,   # 12%
    180: 0.18,   # 18%
}


class StakeCreate(BaseModel):
    token: str = "BRDG"
    amount: float = Field(gt=0)
    lock_days: int = Field(..., description="30|60|90|180")

    @field_validator("lock_days")
    @classmethod
    def valid_lock(cls, v: int) -> int:
        if v not in STAKE_APY:
            raise ValueError(f"lock_days must be one of {list(STAKE_APY)}")
        return v


class StakeOut(BaseModel):
    id: int
    token: str
    amount: float
    lock_days: int
    apy: float
    rewards_earned: float
    status: StakeStatus
    staked_at: datetime
    unlock_at: datetime

    class Config:
        from_attributes = True


class StakeUnlockResponse(BaseModel):
    ok: bool
    id: int
    rewards_earned: float
    total_returned: float


# ---------------------------------------------------------------------------
# Yield farming
# ---------------------------------------------------------------------------
class YieldDeposit(BaseModel):
    protocol: str = Field(..., examples=["uniswap-v3"])
    pool_id: str
    token_a: str
    token_b: str
    amount_usd: float = Field(gt=0)
    auto_compound: bool = True


class YieldOut(BaseModel):
    id: int
    protocol: str
    pool_id: str
    token_a: str
    token_b: str
    liquidity_usd: float
    apy: float
    pending_rewards_usd: float
    total_rewards_claimed_usd: float
    auto_compound: bool
    last_compounded_at: datetime | None = None
    status: YieldStatus
    entered_at: datetime

    class Config:
        from_attributes = True


class YieldCompoundResponse(BaseModel):
    ok: bool
    position_id: int
    rewards_compounded_usd: float
    new_liquidity_usd: float


# ---------------------------------------------------------------------------
# Swaps (DEX)
# ---------------------------------------------------------------------------
class SwapQuoteRequest(BaseModel):
    token_in: str
    token_out: str
    amount_in: float = Field(gt=0)
    slippage_pct: float = Field(0.5, ge=0.01, le=50.0)
    chain_id: int = 1


class SwapQuoteResponse(BaseModel):
    token_in: str
    token_out: str
    amount_in: float
    amount_out_best: float
    amount_out_min: float  # after slippage
    protocol: str
    price_impact_pct: float
    fee_usd: float
    fee_pct: float
    rate: float  # token_out per token_in
    fee_breakdown: dict[str, Any]


class SwapExecuteRequest(BaseModel):
    token_in: str
    token_out: str
    amount_in: float = Field(gt=0)
    amount_out_min: float = Field(gt=0)
    slippage_pct: float = Field(0.5, ge=0.01, le=50.0)
    protocol: str = "uniswap-v3"
    chain_id: int = 1
    tx_hash: str | None = None


class SwapOut(BaseModel):
    id: int
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    fee_usd: float
    fee_pct: float
    protocol: str
    executed_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Tax
# ---------------------------------------------------------------------------
class TaxReportRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    method: str = Field("fifo", pattern="^fifo$")
    format: str = Field("json", pattern="^(json|csv|pdf)$")


class TaxEvent(BaseModel):
    token: str
    amount: float
    cost_basis_usd: float
    proceeds_usd: float
    gain_usd: float
    acquired_at: datetime
    disposed_at: datetime
    holding_days: int
    is_long_term: bool  # >365 days


class TaxReportResponse(BaseModel):
    year: int
    method: str
    total_gains_usd: float
    total_losses_usd: float
    net_gain_usd: float
    short_term_gain_usd: float
    long_term_gain_usd: float
    events: list[TaxEvent]


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------
class RiskScoreResponse(BaseModel):
    user_id: int
    risk_score: float  # 0–100
    var_1d_usd: float
    var_7d_usd: float
    volatility_label: str  # green|yellow|red
    diversification_score: float
    holdings: dict[str, float]  # token → pct of portfolio
    geo_restricted: bool
    audit_status: str  # clean|warning|restricted


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------
class WalletConnectRequest(BaseModel):
    wallet_type: str = Field(..., pattern="^(metamask|walletconnect|ledger)$")
    address: str
    chain_id: int = 1
    signature: str | None = None  # EIP-712 connect signature


class WalletConnectResponse(BaseModel):
    ok: bool
    session_id: int
    address: str
    chain_id: int
    wallet_type: str


class VoucherRedeemRequest(BaseModel):
    code: str


class VoucherRedeemResponse(BaseModel):
    ok: bool
    credits_added: float
    new_balance: float
