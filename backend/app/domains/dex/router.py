"""
DEX domain router.
Ported from BRIDGE_AI_OS/core/app/routes/api.py -- DEX trading endpoints.

Endpoints:
  POST /dex/trade       -- alias for /dex/swap (bossbots compatibility)
  GET  /dex/signals     -- trading signals
  GET  /dex/balance/{address} -- BRDG balance for wallet
  GET  /dex/rates       -- swap rates (1 BRDG = X target)
  POST /dex/swap        -- swap BRDG -> ETH, SOL, USDC, etc.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.domains.dex.services import dex_service
from app.domains.infra.deps import require_jwt

router = APIRouter(prefix="/dex", tags=["dex"])

AuthDep = Annotated[dict, Depends(require_jwt)]


@router.get("/balance/{address}")
async def dex_balance(address: str, _: AuthDep) -> dict[str, Any]:
    """Get BRDG balance for a wallet address. Requires auth."""
    if not address:
        return {"balance": 0.0}
    return {"balance": dex_service.get_balance(address)}


@router.get("/rates")
async def dex_rates(_: AuthDep) -> dict[str, float]:
    """Get swap rates: 1 BRDG = X target. Requires auth."""
    return dex_service.get_rates()


@router.post("/swap")
async def dex_swap(payload: dict[str, Any], _: AuthDep) -> dict[str, Any]:
    """Swap BRDG -> ETH, SOL, USDC, etc. Requires auth."""
    address = payload.get("address") if isinstance(payload, dict) else None
    from_token = payload.get("from_token") or "BRDG"
    to_token = payload.get("to_token")
    amount = payload.get("amount")
    if not address:
        raise HTTPException(status_code=400, detail="address required")
    if not to_token:
        raise HTTPException(status_code=400, detail="to_token required (ETH, SOL, USDC, etc)")
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="amount must be a number")
    result = dex_service.swap(address, from_token, to_token, amount)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "swap failed"))
    return result


@router.post("/trade")
async def dex_trade(trade: dict[str, Any], _: AuthDep) -> dict[str, Any]:
    """Execute DEX trade (bossbots compatibility alias for /swap). Requires auth."""
    asset = trade.get("asset") if isinstance(trade, dict) else None
    if not asset:
        raise HTTPException(status_code=400, detail="asset required")
    # Map trade request to swap format
    address = trade.get("address", "system")
    amount = float(trade.get("amount", 1.0))
    result = dex_service.swap(address, "BRDG", str(asset), amount)
    return result


@router.get("/signals")
async def dex_signals(_: AuthDep) -> dict[str, Any]:
    """Get current DEX trading signals (rates + trends)."""
    rates = dex_service.get_rates()
    signals = []
    for token, rate in rates.items():
        signals.append({
            "pair": f"BRDG/{token}",
            "rate": rate,
            "signal": "neutral",
            "confidence": 0.5,
        })
    return {"ok": True, "signals": signals}
