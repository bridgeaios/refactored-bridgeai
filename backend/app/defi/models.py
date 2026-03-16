"""
DeFi ORM models — SQLAlchemy 2.0 declarative.

12 tables:
  defi_users, defi_refresh_tokens,
  defi_loans, defi_loan_payments,
  defi_stakes,
  defi_yield_positions,
  defi_swaps,
  defi_dex_prices,
  defi_tax_lots,
  defi_subscriptions,
  defi_wallet_sessions,
  defi_portfolio_snapshots
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.defi.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Tier(str, enum.Enum):
    BASIC = "basic"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class LoanStatus(str, enum.Enum):
    OPEN = "open"
    REPAID = "repaid"
    LIQUIDATED = "liquidated"
    DEFAULTED = "defaulted"


class StakeStatus(str, enum.Enum):
    ACTIVE = "active"
    UNLOCKED = "unlocked"
    WITHDRAWN = "withdrawn"


class YieldStatus(str, enum.Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIALING = "trialing"


class SubscriptionPlan(str, enum.Enum):
    STARTER = "starter"      # $499/mo
    GROWTH = "growth"        # $799/mo


class TaxMethod(str, enum.Enum):
    FIFO = "fifo"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class DefiUser(Base):
    __tablename__ = "defi_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_sub: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    picture: Mapped[str | None] = mapped_column(String(512))
    tier: Mapped[Tier] = mapped_column(Enum(Tier), default=Tier.BASIC, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    geo_country: Mapped[str | None] = mapped_column(String(8))  # ISO 3166-1 alpha-2
    native_token_holdings: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    voucher_credits: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_volume_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # relationships
    refresh_tokens: Mapped[list[DefiRefreshToken]] = relationship(back_populates="user", cascade="all, delete-orphan")
    loans: Mapped[list[DefiLoan]] = relationship(back_populates="borrower", cascade="all, delete-orphan")
    stakes: Mapped[list[DefiStake]] = relationship(back_populates="user", cascade="all, delete-orphan")
    yield_positions: Mapped[list[DefiYieldPosition]] = relationship(back_populates="user", cascade="all, delete-orphan")
    swaps: Mapped[list[DefiSwap]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tax_lots: Mapped[list[DefiTaxLot]] = relationship(back_populates="user", cascade="all, delete-orphan")
    subscription: Mapped[DefiSubscription | None] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    wallet_sessions: Mapped[list[DefiWalletSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    portfolio_snapshots: Mapped[list[DefiPortfolioSnapshot]] = relationship(back_populates="user", cascade="all, delete-orphan")


class DefiRefreshToken(Base):
    __tablename__ = "defi_refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    family: Mapped[str] = mapped_column(String(64), nullable=False)  # rotation family for refresh token rotation
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    replaced_by: Mapped[str | None] = mapped_column(String(128))

    user: Mapped[DefiUser] = relationship(back_populates="refresh_tokens")


# ---------------------------------------------------------------------------
# Loans (P2P lending)
# ---------------------------------------------------------------------------
class DefiLoan(Base):
    __tablename__ = "defi_loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    borrower_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    principal_usd: Mapped[float] = mapped_column(Float, nullable=False)
    collateral_usd: Mapped[float] = mapped_column(Float, nullable=False)
    collateral_ratio: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. 1.5 = 150%
    collateral_token: Mapped[str] = mapped_column(String(16), default="ETH", nullable=False)
    collateral_amount: Mapped[float] = mapped_column(Float, nullable=False)
    interest_rate_annual: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. 0.12 = 12% p.a.
    compound_frequency: Mapped[int] = mapped_column(Integer, default=365, nullable=False)  # 365 = daily
    origination_fee_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    outstanding_principal: Mapped[float] = mapped_column(Float, nullable=False)
    accrued_interest: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    liquidation_bonus: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    liquidation_threshold: Mapped[float] = mapped_column(Float, default=1.1, nullable=False)  # 110%
    status: Mapped[LoanStatus] = mapped_column(Enum(LoanStatus), default=LoanStatus.OPEN, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_compounded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    borrower: Mapped[DefiUser] = relationship(back_populates="loans")
    payments: Mapped[list[DefiLoanPayment]] = relationship(back_populates="loan", cascade="all, delete-orphan")


class DefiLoanPayment(Base):
    __tablename__ = "defi_loan_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_loans.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    principal_portion: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    interest_portion: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(String(128))

    loan: Mapped[DefiLoan] = relationship(back_populates="payments")


# ---------------------------------------------------------------------------
# Staking
# ---------------------------------------------------------------------------
class DefiStake(Base):
    __tablename__ = "defi_stakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(16), default="BRDG", nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    lock_days: Mapped[int] = mapped_column(Integer, nullable=False)  # 30|60|90|180
    apy: Mapped[float] = mapped_column(Float, nullable=False)
    rewards_earned: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[StakeStatus] = mapped_column(Enum(StakeStatus), default=StakeStatus.ACTIVE, nullable=False)
    staked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    unlock_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_reward_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[DefiUser] = relationship(back_populates="stakes")


# ---------------------------------------------------------------------------
# Yield Farming
# ---------------------------------------------------------------------------
class DefiYieldPosition(Base):
    __tablename__ = "defi_yield_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    protocol: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "uniswap-v3", "aave"
    pool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    token_a: Mapped[str] = mapped_column(String(16), nullable=False)
    token_b: Mapped[str] = mapped_column(String(16), nullable=False)
    liquidity_usd: Mapped[float] = mapped_column(Float, nullable=False)
    shares: Mapped[float] = mapped_column(Float, nullable=False)
    apy: Mapped[float] = mapped_column(Float, nullable=False)
    pending_rewards_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_rewards_claimed_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    auto_compound: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_compounded_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[YieldStatus] = mapped_column(Enum(YieldStatus), default=YieldStatus.ACTIVE, nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped[DefiUser] = relationship(back_populates="yield_positions")


# ---------------------------------------------------------------------------
# Swaps (DEX)
# ---------------------------------------------------------------------------
class DefiSwap(Base):
    __tablename__ = "defi_swaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_in: Mapped[str] = mapped_column(String(16), nullable=False)
    token_out: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_in: Mapped[float] = mapped_column(Float, nullable=False)
    amount_out: Mapped[float] = mapped_column(Float, nullable=False)
    price_usd_in: Mapped[float] = mapped_column(Float, nullable=False)
    price_usd_out: Mapped[float] = mapped_column(Float, nullable=False)
    protocol: Mapped[str] = mapped_column(String(64), nullable=False)  # "uniswap-v3" | "sushiswap"
    slippage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    fee_usd: Mapped[float] = mapped_column(Float, nullable=False)
    fee_pct: Mapped[float] = mapped_column(Float, nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(String(128))
    chain_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=mainnet
    executed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[DefiUser] = relationship(back_populates="swaps")


class DefiDexPrice(Base):
    __tablename__ = "defi_dex_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="coingecko", nullable=False)
    daily_change_pct: Mapped[float | None] = mapped_column(Float)
    daily_volume_usd: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)


# ---------------------------------------------------------------------------
# Tax lots (FIFO)
# ---------------------------------------------------------------------------
class DefiTaxLot(Base):
    __tablename__ = "defi_tax_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    cost_basis_usd: Mapped[float] = mapped_column(Float, nullable=False)  # per-unit USD
    acquired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    disposed_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime)
    proceeds_usd: Mapped[float | None] = mapped_column(Float)  # total for disposed portion
    gain_usd: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="swap", nullable=False)  # swap|stake_reward|yield

    user: Mapped[DefiUser] = relationship(back_populates="tax_lots")


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------
class DefiSubscription(Base):
    __tablename__ = "defi_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(Enum(SubscriptionPlan), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(16), default="monthly", nullable=False)  # monthly|semi_annual|annual
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    payment_rail: Mapped[str] = mapped_column(String(32), default="paystack", nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    next_billing_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[DefiUser] = relationship(back_populates="subscription")


# ---------------------------------------------------------------------------
# Wallet sessions (MetaMask / WalletConnect / Ledger)
# ---------------------------------------------------------------------------
class DefiWalletSession(Base):
    __tablename__ = "defi_wallet_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_type: Mapped[str] = mapped_column(String(32), nullable=False)  # metamask|walletconnect|ledger
    address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chain_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    connected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped[DefiUser] = relationship(back_populates="wallet_sessions")


# ---------------------------------------------------------------------------
# Portfolio snapshots (for charts + risk)
# ---------------------------------------------------------------------------
class DefiPortfolioSnapshot(Base):
    __tablename__ = "defi_portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("defi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_value_usd: Mapped[float] = mapped_column(Float, nullable=False)
    holdings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # {token: amount}
    prices: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)    # {token: usd_price}
    risk_score: Mapped[float | None] = mapped_column(Float)
    var_1d_usd: Mapped[float | None] = mapped_column(Float)
    snapped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)

    user: Mapped[DefiUser] = relationship(back_populates="portfolio_snapshots")
