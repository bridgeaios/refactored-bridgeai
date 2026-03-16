"""Bridge DeFi Platform - Main FastAPI Application."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func

from app.config import get_settings
from app.models.models import (
    Base,
    Loan,
    RefreshToken,
    Stake,
    Token,
    Transaction,
    TreasuryRecord,
    User,
    UserTier,
    Voucher,
)
from app.models.schemas import (
    BorrowRequest,
    GoogleAuthRequest,
    LiquidateRequest,
    RateLimitInfo,
    RefreshTokenRequest,
    RepayRequest,
    RevokeTokenRequest,
    StakeRequest,
    SwapQuoteResponse,
    SwapRequest,
    TokenResponse,
    TreasuryCollectRequest,
    TreasuryDisburseRequest,
    TreasuryLedgerResponse,
    TreasuryRailsResponse,
    TreasuryStatusResponse,
    UnstakeRequest,
    UpdateTierRequest,
    UserResponse,
    VoucherRequest,
    VoucherResponse,
)
from app.auth import (
    authenticate_google,
    create_access_token,
    decode_token,
    get_tier_limits,
    refresh_access_token,
    revoke_token,
)


settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


app = FastAPI(
    title="Bridge DeFi Platform",
    description="Full-stack DeFi application with P2P lending, staking, and DEX aggregation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ==================== Auth Endpoints ====================


@app.post("/api/v1/auth/google", response_model=TokenResponse)
async def google_login(request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        _, token_response = await authenticate_google(request.code, db)
        return token_response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google auth failed: {str(e)}")


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    token_response = await refresh_access_token(request.refresh_token, db)
    if not token_response:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return token_response


@app.post("/api/v1/auth/revoke")
async def revoke(request: RevokeTokenRequest, db: AsyncSession = Depends(get_db)):
    success = await revoke_token(request.token, db)
    if not success:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "revoked"}


# ==================== User Endpoints ====================


@app.get("/api/v1/user/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@app.patch("/api/v1/user/tier", response_model=UserResponse)
async def update_tier(
    request: UpdateTierRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.tier = request.tier
    await db.commit()
    await db.refresh(current_user)
    return current_user


@app.get("/api/v1/user/rate-limit", response_model=RateLimitInfo)
async def get_rate_limit(current_user: User = Depends(get_current_user)):
    limits = get_tier_limits(current_user.tier)
    return RateLimitInfo(
        limit=limits["rate_limit"],
        remaining=limits["rate_limit"],
        reset=int((datetime.now(timezone.utc) + timedelta(minutes=1)).timestamp()),
    )


# ==================== Lending Endpoints ====================


@app.post("/api/v1/lending/borrow")
async def borrow(
    request: BorrowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limits = get_tier_limits(current_user.tier)

    result = await db.execute(
        select(Token).where(Token.symbol == request.token.value)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    result = await db.execute(
        select(Token).where(Token.symbol == request.collateral_token.value)
    )
    collateral_token = result.scalar_one_or_none()

    loan = Loan(
        user_id=current_user.id,
        token_id=token.id,
        amount=request.amount,
        collateral_amount=request.collateral_amount,
        collateral_token_id=collateral_token.id if collateral_token else None,
        interest_rate=limits["fee"],
        collateral_ratio=request.collateral_ratio,
    )
    db.add(loan)
    await db.commit()
    await db.refresh(loan)

    return {
        "id": loan.id,
        "amount": loan.amount,
        "collateral_amount": loan.collateral_amount,
        "interest_rate": loan.interest_rate,
        "collateral_ratio": loan.collateral_ratio,
    }


@app.post("/api/v1/lending/repay")
async def repay(
    request: RepayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Loan).where(
            Loan.id == request.loan_id,
            Loan.user_id == current_user.id,
        )
    )
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if request.amount >= loan.amount:
        await db.delete(loan)
    else:
        loan.amount = loan.amount - request.amount

    await db.commit()
    return {"status": "repaid", "remaining": loan.amount if request.amount < loan.amount else 0}


@app.post("/api/v1/lending/liquidate")
async def liquidate(
    request: LiquidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Loan).where(
            Loan.id == request.loan_id,
            Loan.is_liquidated == False,
        )
    )
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    bonus = float(loan.amount) * settings.liquidation_bonus

    result = await db.execute(select(User).where(User.id == loan.user_id))
    borrower = result.scalar_one_or_none()
    if borrower:
        borrower.transaction_volume += bonus

    loan.is_liquidated = True
    await db.commit()

    return {
        "status": "liquidated",
        "bonus": bonus,
        "liquidator": current_user.id,
    }


# ==================== Staking Endpoints ====================


@app.post("/api/v1/staking/stake")
async def stake(
    request: StakeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apy_map = {
        30: settings.apy_30_days,
        60: settings.apy_60_days,
        90: settings.apy_90_days,
        180: settings.apy_180_days,
    }
    apy = apy_map.get(request.lock_period_days, settings.apy_30_days)

    result = await db.execute(
        select(Token).where(Token.symbol == request.token.value)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    stake = Stake(
        user_id=current_user.id,
        token_id=token.id,
        amount=request.amount,
        lock_period_days=request.lock_period_days,
        apy=apy,
        end_date=datetime.now(timezone.utc) + timedelta(days=request.lock_period_days),
    )
    db.add(stake)

    current_user.staking_amount += float(request.amount)

    await db.commit()
    await db.refresh(stake)

    return {
        "id": stake.id,
        "amount": stake.amount,
        "lock_period_days": stake.lock_period_days,
        "apy": stake.apy,
        "end_date": stake.end_date,
    }


@app.post("/api/v1/staking/unstake")
async def unstake(
    request: UnstakeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Stake).where(
            Stake.id == request.stake_id,
            Stake.user_id == current_user.id,
        )
    )
    stake = result.scalar_one_or_none()
    if not stake:
        raise HTTPException(status_code=404, detail="Stake not found")

    if datetime.now(timezone.utc) < stake.end_date:
        raise HTTPException(status_code=400, detail="Stake lock period not yet complete")

    rewards = float(stake.amount) * stake.apy * (stake.lock_period_days / 365)

    stake.is_claimed = True
    stake.claimed_at = datetime.now(timezone.utc)
    current_user.staking_amount -= float(stake.amount)

    await db.commit()

    return {
        "status": "claimed",
        "principal": stake.amount,
        "rewards": rewards,
    }


@app.get("/api/v1/staking/rewards")
async def get_rewards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Stake).where(
            Stake.user_id == current_user.id,
            Stake.is_claimed == False,
        )
    )
    stakes = result.scalars().all()

    total_pending = 0.0
    for s in stakes:
        days_staked = (datetime.now(timezone.utc) - s.start_date).days
        pending = float(s.amount) * s.apy * (days_staked / 365)
        total_pending += pending

    return {"pending_rewards": total_pending, "active_stakes": len(stakes)}


# ==================== DEX Endpoints ====================


@app.get("/api/v1/dex/quote", response_model=SwapQuoteResponse)
async def get_quote(request: SwapRequest):
    amount_out = request.amount_in * Decimal("0.95")
    minimum_amount_out = amount_out * Decimal(str(1 - request.slippage))
    fee = amount_out * Decimal("0.003")

    return SwapQuoteResponse(
        token_in=request.token_in.value,
        token_out=request.token_out.value,
        amount_in=request.amount_in,
        amount_out=amount_out,
        minimum_amount_out=minimum_amount_out,
        fee=fee,
        route=[request.token_in.value, request.token_out.value],
    )


@app.post("/api/v1/dex/swap")
async def swap(
    request: SwapRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limits = get_tier_limits(current_user.tier)
    amount_out = float(request.amount_in) * 0.95
    fee = amount_out * limits["fee"]

    tx = Transaction(
        user_id=current_user.id,
        tx_type="swap",
        token_in=request.token_in.value,
        token_out=request.token_out.value,
        amount_in=request.amount_in,
        amount_out=amount_out,
        fee=fee,
        status="completed",
    )
    db.add(tx)

    current_user.transaction_volume += float(request.amount_in)

    await db.commit()
    await db.refresh(tx)

    return {
        "tx_hash": f"0x{tx.id:064x}",
        "status": tx.status,
        "fee": fee,
    }


# ==================== Treasury Endpoints ====================


@app.post("/api/v1/treasury/collect")
async def treasury_collect(
    request: TreasuryCollectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.tier not in [UserTier.GOLD, UserTier.PLATINUM]:
        raise HTTPException(status_code=403, detail="Tier not authorized")

    record = TreasuryRecord(
        project=request.project,
        rail=request.rail,
        currency=request.currency,
        amount=request.amount,
        tx_type="collection",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {"id": record.id, "status": "collected"}


@app.get("/api/v1/treasury/status", response_model=TreasuryStatusResponse)
async def treasury_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            TreasuryRecord.project,
            TreasuryRecord.rail,
            TreasuryRecord.currency,
            func.sum(TreasuryRecord.amount),
        ).group_by(
            TreasuryRecord.project,
            TreasuryRecord.rail,
            TreasuryRecord.currency,
        )
    )
    records = result.all()

    total = sum(float(r[3] or 0) for r in records)
    by_project: dict[str, float] = {}
    by_rail: dict[str, float] = {}
    by_currency: dict[str, float] = {}

    for proj, rail, curr, amt in records:
        by_project[proj] = by_project.get(proj, 0) + float(amt or 0)
        by_rail[rail] = by_rail.get(rail, 0) + float(amt or 0)
        by_currency[curr] = by_currency.get(curr, 0) + float(amt or 0)

    return TreasuryStatusResponse(
        ubi_allocation=total * settings.treasury_ubi_percent,
        treasury_allocation=total * settings.treasury_reserve_percent,
        operations_allocation=total * settings.treasury_ops_percent,
        founder_allocation=total * settings.treasury_founder_percent,
        total=total,
        by_project=by_project,
        by_rail=by_rail,
        by_currency=by_currency,
    )


@app.get("/api/v1/treasury/ledger", response_model=list[TreasuryLedgerResponse])
async def treasury_ledger(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TreasuryRecord)
        .order_by(TreasuryRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    records = result.scalars().all()
    return records


@app.get("/api/v1/treasury/rails", response_model=TreasuryRailsResponse)
async def treasury_rails():
    return TreasuryRailsResponse(
        rails={
            "paystack": {"status": True, "currencies": ["ZAR", "NGN"]},
            "paypal": {"status": True, "currencies": ["USD", "EUR", "GBP"]},
            "crypto": {"status": True, "currencies": ["ETH", "SOL", "USDC", "USDT", "BRDG"]},
        },
        supported_currencies=["ZAR", "NGN", "USD", "EUR", "GBP", "ETH", "SOL", "USDC", "USDT", "BRDG"],
    )


@app.post("/api/v1/treasury/disburse")
async def treasury_disburse(
    request: TreasuryDisburseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.tier != UserTier.PLATINUM:
        raise HTTPException(status_code=403, detail="Tier not authorized")

    record = TreasuryRecord(
        project=request.project,
        rail=request.rail,
        currency=request.currency,
        amount=request.amount,
        tx_type="disbursement",
        description=request.reason,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {"id": record.id, "status": "disbursed"}


# ==================== Payment Webhooks ====================


@app.post("/api/v1/payments/webhook/paystack")
async def paystack_webhook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    event = payload.get("event")
    data = payload.get("data", {})

    if event == "charge.success":
        amount = data.get("amount", 0) / 100
        currency = data.get("currency", "NGN")

        record = TreasuryRecord(
            project="payments",
            rail="paystack",
            currency=currency,
            amount=amount,
            tx_type="deposit",
            tx_hash=data.get("reference"),
        )
        db.add(record)
        await db.commit()

    return {"status": "received"}


@app.post("/api/v1/payments/webhook/paypal")
async def paypal_webhook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    resource = payload.get("resource", {})
    amount = resource.get("amount", {})
    value = amount.get("value", "0")
    currency = amount.get("currency_code", "USD")

    record = TreasuryRecord(
        project="payments",
        rail="paypal",
        currency=currency,
        amount=float(value),
        tx_type="deposit",
    )
    db.add(record)
    await db.commit()

    return {"status": "received"}


@app.post("/api/v1/payments/webhook/crypto")
async def crypto_webhook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    record = TreasuryRecord(
        project="payments",
        rail="crypto",
        currency=payload.get("token", "ETH"),
        amount=payload.get("amount", 0),
        tx_type="deposit",
        tx_hash=payload.get("tx_hash"),
    )
    db.add(record)
    await db.commit()

    return {"status": "received"}


# ==================== Voucher Endpoints ====================


@app.post("/api/v1/voucher/redeem", response_model=VoucherResponse)
async def redeem_voucher(
    request: VoucherRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Voucher).where(
            Voucher.code == request.code,
            Voucher.is_used == False,
        )
    )
    voucher = result.scalar_one_or_none()

    if not voucher:
        raise HTTPException(status_code=404, detail="Invalid or used voucher")

    if voucher.expires_at and voucher.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Voucher expired")

    voucher.is_used = True
    voucher.user_id = current_user.id
    await db.commit()

    return voucher


# ==================== Health Check ====================


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {"message": "Bridge DeFi Platform API", "version": "1.0.0"}
