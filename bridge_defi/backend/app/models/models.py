"""Database models for Bridge DeFi Platform."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    Integer,
    Numeric,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class UserTier(str, Enum):
    BASIC = "basic"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    tier: Mapped[UserTier] = mapped_column(
        SQLEnum(UserTier), default=UserTier.BASIC
    )
    wallet_address: Mapped[Optional[str]] = mapped_column(String(42))
    staking_amount: Mapped[float] = mapped_column(Float, default=0.0)
    transaction_volume: Mapped[float] = mapped_column(Float, default=0.0)
    subscription_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    loans: Mapped[list["Loan"]] = relationship(back_populates="user")
    stakes: Mapped[list["Stake"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    vouchers: Mapped[list["Voucher"]] = relationship(back_populates="user")


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(42))
    decimals: Mapped[int] = mapped_column(Integer, default=18)
    is_stablecoin: Mapped[bool] = mapped_column(Boolean, default=False)
    chain_id: Mapped[int] = mapped_column(Integer, default=1)

    loans: Mapped[list["Loan"]] = relationship(back_populates="token")
    stakes: Mapped[list["Stake"]] = relationship(back_populates="token")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_id: Mapped[int] = mapped_column(ForeignKey("tokens.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(78, 0), nullable=False)
    collateral_amount: Mapped[float] = mapped_column(Numeric(78, 0), nullable=False)
    collateral_token_id: Mapped[int] = mapped_column(ForeignKey("tokens.id"))
    interest_rate: Mapped[float] = mapped_column(Float, nullable=False)
    collateral_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    is_liquidated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="loans")
    token: Mapped["Token"] = relationship(foreign_keys=[token_id])
    collateral_token: Mapped[Optional["Token"]] = relationship(
        foreign_keys=[collateral_token_id]
    )


class Stake(Base):
    __tablename__ = "stakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_id: Mapped[int] = mapped_column(ForeignKey("tokens.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(78, 0), nullable=False)
    lock_period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    apy: Mapped[float] = mapped_column(Float, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_claimed: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="stakes")
    token: Mapped["Token"] = relationship(back_populates="stakes")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tx_type: Mapped[str] = mapped_column(String(50), nullable=False)
    token_in: Mapped[Optional[str]] = mapped_column(String(20))
    token_out: Mapped[Optional[str]] = mapped_column(String(20))
    amount_in: Mapped[Optional[float]] = mapped_column(Numeric(78, 0))
    amount_out: Mapped[Optional[float]] = mapped_column(Numeric(78, 0))
    fee: Mapped[float] = mapped_column(Numeric(78, 0), default=0)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="transactions")


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    discount_percent: Mapped[float] = mapped_column(Float, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="vouchers")


class TreasuryRecord(Base):
    __tablename__ = "treasury_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(50), nullable=False)
    rail: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(78, 0), nullable=False)
    tx_type: Mapped[str] = mapped_column(String(20), nullable=False)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
