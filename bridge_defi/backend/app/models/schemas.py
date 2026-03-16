"""Pydantic schemas for request/response validation."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserTier(str, Enum):
    BASIC = "basic"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class TokenSymbol(str, Enum):
    ETH = "ETH"
    USDC = "USDC"
    USDT = "USDT"
    BRDG = "BRDG"
    SOL = "SOL"


# Auth Schemas
class GoogleAuthRequest(BaseModel):
    code: str = Field(..., description="Google OAuth authorization code")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RevokeTokenRequest(BaseModel):
    token: str


# User Schemas
class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    tier: UserTier
    wallet_address: Optional[str]
    staking_amount: float
    transaction_volume: float
    subscription_end: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateTierRequest(BaseModel):
    tier: UserTier


# Lending Schemas
class BorrowRequest(BaseModel):
    token: TokenSymbol
    amount: Decimal = Field(..., gt=0, description="Amount to borrow")
    collateral_token: TokenSymbol
    collateral_amount: Decimal = Field(..., gt=0, description="Collateral amount")
    collateral_ratio: float = Field(
        ..., ge=1.10, le=1.50, description="Collateral ratio 110%-150%"
    )


class RepayRequest(BaseModel):
    loan_id: int
    amount: Decimal = Field(..., gt=0)


class LiquidateRequest(BaseModel):
    loan_id: int


class LoanResponse(BaseModel):
    id: int
    user_id: int
    token: str
    amount: Decimal
    collateral_amount: Decimal
    collateral_token: str
    interest_rate: float
    collateral_ratio: float
    is_liquidated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Staking Schemas
class StakeRequest(BaseModel):
    token: TokenSymbol
    amount: Decimal = Field(..., gt=0)
    lock_period_days: int = Field(..., ge=30, le=180)


class UnstakeRequest(BaseModel):
    stake_id: int


class StakeResponse(BaseModel):
    id: int
    user_id: int
    token: str
    amount: Decimal
    lock_period_days: int
    apy: float
    start_date: datetime
    end_date: datetime
    is_claimed: bool

    model_config = {"from_attributes": True}


# DEX Schemas
class SwapRequest(BaseModel):
    token_in: TokenSymbol
    token_out: TokenSymbol
    amount_in: Decimal = Field(..., gt=0)
    slippage: float = Field(default=0.005, ge=0.001, le=0.05)
    dex: Optional[str] = Field(default=None, description="uniswap or sushiswap")


class SwapQuoteResponse(BaseModel):
    token_in: str
    token_out: str
    amount_in: Decimal
    amount_out: Decimal
    minimum_amount_out: Decimal
    fee: Decimal
    route: list[str]


class SwapResponse(BaseModel):
    tx_hash: str
    status: str


# Treasury Schemas
class TreasuryStatusResponse(BaseModel):
    ubi_allocation: float
    treasury_allocation: float
    operations_allocation: float
    founder_allocation: float
    total: float
    by_project: dict[str, float]
    by_rail: dict[str, float]
    by_currency: dict[str, float]


class TreasuryLedgerResponse(BaseModel):
    id: int
    project: str
    rail: str
    currency: str
    amount: float
    tx_type: str
    tx_hash: Optional[str]
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TreasuryRailsResponse(BaseModel):
    rails: dict[str, dict[str, bool]]
    supported_currencies: list[str]


class TreasuryCollectRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    project: str
    rail: str
    currency: str


class TreasuryDisburseRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    recipient: str
    project: str
    rail: str
    currency: str
    reason: str


# Payment Webhook Schemas
class PaystackWebhook(BaseModel):
    event: str
    data: dict


class PayPalWebhook(BaseModel):
    event_type: str
    resource: dict


class CryptoWebhook(BaseModel):
    tx_hash: str
    from_address: str
    to_address: str
    amount: Decimal
    token: str
    confirmations: int


# Voucher Schemas
class VoucherRequest(BaseModel):
    code: str


class VoucherResponse(BaseModel):
    id: int
    code: str
    discount_percent: float
    is_used: bool

    model_config = {"from_attributes": True}


# Risk Management Schemas
class PortfolioResponse(BaseModel):
    total_value: float
    allocation: dict[str, float]
    risk_score: int = Field(..., ge=0, le=100)
    volatility: str  # "low", "medium", "high"


# Tax Report Schemas
class TaxReportRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2030)
    format: str = Field(default="csv", pattern="^(csv|pdf)$")


# Rate Limit Schemas
class RateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset: int
