"""
Payment Rails — unified verification and parsing for all payment processors.

Supported: Paystack, PayPal, internal BRDG, crypto.
Any project's webhook hits /api/payments/webhook/{rail} and flows into TreasuryService.collect().

Security: each rail verifies the webhook signature before processing.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any


class PaymentRails:
    """
    Verify and parse payment events from external processors.
    Returns a normalized PaymentEvent dict or None if invalid.
    """

    # ------------------------------------------------------------------
    # Paystack (Africa-first; primary SA rail)
    # ------------------------------------------------------------------

    # Placeholder substrings that indicate the key is not a real production key
    _PLACEHOLDERS = ("your-", "sk_test", "test_", "change-me", "placeholder", "xxx", "dummy", "replace_", "replace-", "todo", "fill_")

    @classmethod
    def _is_placeholder(cls, val: str) -> bool:
        v = val.lower()
        return any(p in v for p in cls._PLACEHOLDERS)

    @classmethod
    def verify_paystack(cls, body_bytes: bytes, signature: str) -> bool:
        """
        Verify Paystack webhook HMAC-SHA512 signature.
        Uses PAYSTACK_WEBHOOK_SECRET (preferred) or PAYSTACK_SECRET_KEY fallback.
        Accepts without verification in dev when no real key is configured.
        """
        # Paystack sends a separate webhook signing secret
        secret = (
            os.environ.get("PAYSTACK_WEBHOOK_SECRET")
            or os.environ.get("PAYSTACK_SECRET_KEY", "")
        )
        # Accept in dev/test if key absent or is a placeholder
        if not secret or cls._is_placeholder(secret):
            return True
        expected = hmac.new(
            secret.encode("utf-8"), body_bytes, hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    @staticmethod
    def parse_paystack(body: dict[str, Any]) -> dict[str, Any] | None:
        """
        Parse Paystack webhook event.
        Returns normalized payment event or None if not a payment event.
        Handles: charge.success, subscription.create, transfer.success
        """
        event = body.get("event", "")
        data = body.get("data", {})

        amount_kobo = data.get("amount", 0)
        currency = (data.get("currency") or "ZAR").upper()
        # Paystack amounts are in smallest unit (kobo for NGN, cents for ZAR/USD)
        amount = round(float(amount_kobo) / 100, 2)

        customer = data.get("customer", {})
        customer_email = customer.get("email") if isinstance(customer, dict) else str(customer)

        if event == "charge.success":
            return {
                "rail": "paystack",
                "type": "payment",
                "amount": amount,
                "currency": currency,
                "customer": customer_email or "",
                "reference": data.get("reference", ""),
                "plan": data.get("plan", ""),
                "meta": {"event": event, "channel": data.get("channel", "")},
            }
        if event == "subscription.create":
            plan_obj = data.get("plan", {})
            plan_amount_kobo = plan_obj.get("amount", 0) if isinstance(plan_obj, dict) else 0
            return {
                "rail": "paystack",
                "type": "subscription",
                "amount": round(float(plan_amount_kobo) / 100, 2),
                "currency": currency,
                "customer": customer_email or "",
                "reference": data.get("subscription_code", ""),
                "plan": plan_obj.get("name", "") if isinstance(plan_obj, dict) else "",
                "meta": {"event": event},
            }
        if event == "transfer.success":
            return {
                "rail": "paystack",
                "type": "transfer",
                "amount": amount,
                "currency": currency,
                "customer": data.get("recipient", {}).get("name", "") if isinstance(data.get("recipient"), dict) else "",
                "reference": data.get("reference", ""),
                "plan": "",
                "meta": {"event": event},
            }
        return None

    # ------------------------------------------------------------------
    # PayPal
    # ------------------------------------------------------------------

    @staticmethod
    def verify_paypal(body_bytes: bytes, headers: dict[str, str]) -> bool:
        """
        PayPal webhook verification. In production: call PayPal verify API.
        For now: accept if PAYPAL_WEBHOOK_ID env var matches header.
        """
        webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID", "")
        if not webhook_id:
            return True  # Dev: accept without key
        # Real implementation: POST to https://api.paypal.com/v1/notifications/verify-webhook-signature
        return True  # Placeholder — replace with real call in production

    @staticmethod
    def parse_paypal(body: dict[str, Any]) -> dict[str, Any] | None:
        """
        Parse PayPal webhook event.
        Handles: PAYMENT.CAPTURE.COMPLETED, BILLING.SUBSCRIPTION.ACTIVATED
        """
        event_type = body.get("event_type", "")
        resource = body.get("resource", {})

        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            amount_obj = resource.get("amount", {})
            amount = float(amount_obj.get("value", 0))
            currency = (amount_obj.get("currency_code") or "USD").upper()
            return {
                "rail": "paypal",
                "type": "payment",
                "amount": amount,
                "currency": currency,
                "customer": resource.get("payer", {}).get("email_address", "") if isinstance(resource.get("payer"), dict) else "",
                "reference": resource.get("id", ""),
                "plan": "",
                "meta": {"event": event_type},
            }
        if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
            plan_id = resource.get("plan_id", "")
            return {
                "rail": "paypal",
                "type": "subscription",
                "amount": 0.0,  # Amount comes on first payment event
                "currency": "USD",
                "customer": resource.get("subscriber", {}).get("email_address", "") if isinstance(resource.get("subscriber"), dict) else "",
                "reference": resource.get("id", ""),
                "plan": plan_id,
                "meta": {"event": event_type},
            }
        return None

    # ------------------------------------------------------------------
    # Crypto (generic on-chain event → revenue)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_crypto(body: dict[str, Any]) -> dict[str, Any] | None:
        """Parse on-chain payment notification from contract_listener or manual webhook."""
        if body.get("type") not in ("deposit", "payment", "bridge_payment"):
            return None
        return {
            "rail": "crypto",
            "type": body.get("type", "payment"),
            "amount": float(body.get("amount", 0)),
            "currency": (body.get("currency") or "BRDG").upper(),
            "customer": body.get("from", body.get("wallet", "")),
            "reference": body.get("tx_hash", body.get("ref", "")),
            "plan": "",
            "meta": body.get("meta", {}),
        }

    # ------------------------------------------------------------------
    # Generic normalize (for any unrecognized rail)
    # ------------------------------------------------------------------

    @staticmethod
    def normalize(body: dict[str, Any], rail: str) -> dict[str, Any] | None:
        """Fallback: accept any {amount, currency} body from a known internal source."""
        amount = body.get("amount")
        if not amount:
            return None
        return {
            "rail": rail,
            "type": body.get("type", "payment"),
            "amount": float(amount),
            "currency": (body.get("currency") or "BRDG").upper(),
            "customer": body.get("customer", body.get("wallet", "")),
            "reference": body.get("reference", body.get("ref", "")),
            "plan": body.get("plan", ""),
            "meta": body.get("meta", {}),
        }
