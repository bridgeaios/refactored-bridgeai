"""
Treasury API — unified payment backbone for all Bridge AI OS projects.

Any project (AOE, Supaco, Taurus, bridge-backend, Next.js) calls:
  POST /api/treasury/collect  { amount, currency, source_project, method, type, meta }

Payment webhooks (Paystack, PayPal) POST to:
  POST /api/payments/webhook/paystack
  POST /api/payments/webhook/paypal
  POST /api/payments/webhook/crypto

All flows auto-split into: UBI 40% · Treasury 30% · Ops 20% · Founder 10%
"""
import json

from fastapi import APIRouter, HTTPException, Request

from app.runtime import treasury_service
from app.services.payment_rails import PaymentRails

router = APIRouter()


# ------------------------------------------------------------------
# Treasury core
# ------------------------------------------------------------------

@router.post("/treasury/collect")
async def treasury_collect(payload: dict):
    """
    Collect revenue from any project into the unified treasury.
    Required: amount (float)
    Optional: currency (default BRDG), source_project, method, type, meta
    """
    amount = payload.get("amount")
    if not amount:
        raise HTTPException(status_code=400, detail="amount required")
    try:
        amount = float(amount)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail="amount must be a number") from e

    result = await treasury_service.collect(
        amount=amount,
        currency=str(payload.get("currency", "BRDG")).upper(),
        source_project=str(payload.get("source_project", "unknown")),
        method=str(payload.get("method", "internal")),
        type_=str(payload.get("type", "revenue")),
        meta=payload.get("meta") if isinstance(payload.get("meta"), dict) else {},
    )
    return result


@router.get("/treasury/status")
async def treasury_status():
    """Full treasury status: totals, buckets, by-project, by-method, by-currency."""
    status = await treasury_service.get_status()
    return {"ok": True, **status}


@router.get("/treasury/ledger")
async def treasury_ledger(limit: int = 50):
    """Recent treasury transactions (most recent first). Max 200."""
    limit = max(1, min(int(limit), 200))
    entries = await treasury_service.get_ledger(limit)
    return {"ok": True, "count": len(entries), "entries": entries}


@router.post("/treasury/disburse")
async def treasury_disburse(payload: dict):
    """
    Record a treasury disbursement from a bucket.
    Required: bucket (ubi|treasury|ops|founder), amount, destination
    Optional: authorized_by
    """
    bucket = payload.get("bucket")
    amount = payload.get("amount")
    destination = payload.get("destination", "")
    if not bucket or not amount:
        raise HTTPException(status_code=400, detail="bucket and amount required")
    try:
        amount = float(amount)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail="amount must be a number") from e

    result = await treasury_service.disburse(
        bucket=str(bucket),
        amount=amount,
        destination=str(destination),
        authorized_by=str(payload.get("authorized_by", "founder")),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason", "disburse failed"))
    return result


@router.get("/treasury/rails")
async def list_rails():
    """List all supported payment rails and their status."""
    import os
    rails = [
        {"id": "internal", "label": "Internal (BRDG)", "status": "active", "currencies": ["BRDG"]},
        {"id": "paystack", "label": "Paystack", "status": "active" if os.environ.get("PAYSTACK_SECRET_KEY") else "no-key", "currencies": ["ZAR", "NGN", "USD", "GHS"]},
        {"id": "paypal", "label": "PayPal", "status": "active" if os.environ.get("PAYPAL_CLIENT_ID") else "no-key", "currencies": ["USD", "EUR", "GBP"]},
        {"id": "crypto", "label": "Crypto (BRDG/ETH/SOL)", "status": "active", "currencies": ["BRDG", "ETH", "BTC", "SOL"]},
        {"id": "subscription", "label": "Subscription revenue", "status": "active", "currencies": ["USD", "ZAR", "BRDG"]},
        {"id": "sensor", "label": "Sensor / passive income", "status": "active", "currencies": ["BRDG"]},
        {"id": "trade", "label": "Boss-bot trade fees", "status": "active", "currencies": ["BRDG"]},
        {"id": "marketplace", "label": "Marketplace fees", "status": "active", "currencies": ["BRDG"]},
    ]
    return {"ok": True, "rails": rails, "split": {"ubi": "40%", "treasury": "30%", "ops": "20%", "founder": "10%"}}


# ------------------------------------------------------------------
# Payment webhooks — external processors POST here
# ------------------------------------------------------------------

@router.post("/payments/webhook/paystack")
async def webhook_paystack(request: Request):
    """
    Paystack webhook endpoint.
    Set this URL in Paystack dashboard: https://api.bridge-ai-os.tech/api/payments/webhook/paystack
    """
    body_bytes = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not PaymentRails.verify_paystack(body_bytes, signature):
        raise HTTPException(status_code=401, detail="invalid Paystack signature")

    try:
        body = json.loads(body_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid JSON") from e

    event = PaymentRails.parse_paystack(body)
    if not event:
        return {"ok": True, "skipped": True, "reason": "non-payment event"}

    result = await treasury_service.collect(
        amount=event["amount"],
        currency=event["currency"],
        source_project=event.get("plan") or "paystack-direct",
        method="paystack",
        type_=event["type"],
        meta={"customer": event["customer"], "reference": event["reference"], **event.get("meta", {})},
    )
    return {"ok": True, "collected": result.get("entry", {}).get("amount_brdg", 0)}


@router.post("/payments/webhook/paypal")
async def webhook_paypal(request: Request):
    """
    PayPal webhook endpoint.
    Set in PayPal developer dashboard: https://api.bridge-ai-os.tech/api/payments/webhook/paypal
    """
    body_bytes = await request.body()
    headers = dict(request.headers)

    if not PaymentRails.verify_paypal(body_bytes, headers):
        raise HTTPException(status_code=401, detail="invalid PayPal signature")

    try:
        body = json.loads(body_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid JSON") from e

    event = PaymentRails.parse_paypal(body)
    if not event or event["amount"] <= 0:
        return {"ok": True, "skipped": True, "reason": "non-payment or zero-amount event"}

    result = await treasury_service.collect(
        amount=event["amount"],
        currency=event["currency"],
        source_project=event.get("plan") or "paypal-direct",
        method="paypal",
        type_=event["type"],
        meta={"customer": event["customer"], "reference": event["reference"], **event.get("meta", {})},
    )
    return {"ok": True, "collected": result.get("entry", {}).get("amount_brdg", 0)}


@router.post("/payments/webhook/crypto")
async def webhook_crypto(request: Request):
    """
    Crypto / on-chain payment webhook.
    Called by contract_listener or external bridge node.
    """
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid JSON") from e

    event = PaymentRails.parse_crypto(body)
    if not event:
        return {"ok": True, "skipped": True, "reason": "unrecognized crypto event"}

    result = await treasury_service.collect(
        amount=event["amount"],
        currency=event["currency"],
        source_project="crypto",
        method="crypto",
        type_=event["type"],
        meta={"wallet": event["customer"], "tx_hash": event["reference"], **event.get("meta", {})},
    )
    return {"ok": True, "collected": result.get("entry", {}).get("amount_brdg", 0)}


@router.post("/payments/webhook/{rail}")
async def webhook_generic(rail: str, request: Request):
    """
    Generic webhook for any internal project.
    Called by AOE, Supaco, Taurus, etc. to route revenue into the unified treasury.
    Body: { amount, currency, source_project, type, customer, reference, meta }
    """
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid JSON") from e

    event = PaymentRails.normalize(body, rail)
    if not event:
        raise HTTPException(status_code=400, detail="amount required")

    result = await treasury_service.collect(
        amount=event["amount"],
        currency=event["currency"],
        source_project=str(body.get("source_project", rail)),
        method=rail,
        type_=event["type"],
        meta={"customer": event["customer"], "reference": event["reference"], **event.get("meta", {})},
    )
    return {"ok": True, "collected": result.get("entry", {}).get("amount_brdg", 0)}
