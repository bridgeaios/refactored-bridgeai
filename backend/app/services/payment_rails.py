"""
Payment Rails — unified verification and parsing for all payment processors.

Supported: Paystack, PayPal, PayFast, internal BRDG, crypto.
Any project's webhook hits /api/payments/webhook/{rail} and flows into TreasuryService.collect().

Security: each rail verifies the webhook signature before processing.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

import httpx

_log = logging.getLogger("payment_rails")


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
    async def _get_paypal_access_token() -> str | None:
        """
        Obtain a PayPal OAuth2 access token using client credentials.
        Returns None if credentials are missing or the request fails.
        """
        client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
        client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return None
        base = (
            "https://api-m.sandbox.paypal.com"
            if os.environ.get("PAYPAL_SANDBOX", "1") == "1"
            else "https://api-m.paypal.com"
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{base}/v1/oauth2/token",
                    data={"grant_type": "client_credentials"},
                    auth=(client_id, client_secret),
                )
                resp.raise_for_status()
                return resp.json().get("access_token")
        except Exception:
            _log.exception("PayPal access token fetch failed")
            return None

    @staticmethod
    async def verify_paypal(body_bytes: bytes, headers: dict[str, str]) -> bool:
        """
        Verify a PayPal webhook event using the official
        POST /v1/notifications/verify-webhook-signature API.

        Returns True only if PayPal confirms the signature is valid.
        Rejects (returns False) on: missing config, HTTP errors, network
        failures, or any verification_status other than 'SUCCESS'.

        Required env vars:
          PAYPAL_WEBHOOK_ID      — the webhook ID from PayPal dashboard
          PAYPAL_CLIENT_ID       — REST API app client ID
          PAYPAL_CLIENT_SECRET   — REST API app client secret
          PAYPAL_SANDBOX         — "1" for sandbox (default), "0" for live
        """
        webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID", "")
        if not webhook_id:
            _log.warning("PayPal webhook rejected: PAYPAL_WEBHOOK_ID not configured")
            return False

        access_token = await PaymentRails._get_paypal_access_token()
        if not access_token:
            _log.error("PayPal webhook rejected: could not obtain access token")
            return False

        # PayPal requires the raw body as a parsed JSON object in the payload
        import json as _json
        try:
            body_obj = _json.loads(body_bytes)
        except Exception:
            _log.warning("PayPal webhook rejected: body is not valid JSON")
            return False

        base = (
            "https://api-m.sandbox.paypal.com"
            if os.environ.get("PAYPAL_SANDBOX", "1") == "1"
            else "https://api-m.paypal.com"
        )

        payload = {
            "transmission_id":   headers.get("paypal-transmission-id", ""),
            "transmission_time": headers.get("paypal-transmission-time", ""),
            "cert_url":          headers.get("paypal-cert-url", ""),
            "auth_algo":         headers.get("paypal-auth-algo", ""),
            "transmission_sig":  headers.get("paypal-transmission-sig", ""),
            "webhook_id":        webhook_id,
            "webhook_event":     body_obj,
        }

        # All required fields must be present
        missing = [k for k, v in payload.items() if not v and k != "webhook_event"]
        if missing:
            _log.warning("PayPal webhook rejected: missing headers %s", missing)
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{base}/v1/notifications/verify-webhook-signature",
                    json=payload,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                status = resp.json().get("verification_status", "")
                if status != "SUCCESS":
                    _log.warning("PayPal webhook rejected: verification_status=%s", status)
                    return False
                return True
        except httpx.HTTPStatusError as exc:
            _log.error("PayPal verify API HTTP error: %s", exc.response.status_code)
            return False
        except Exception:
            _log.exception("PayPal verify API request failed")
            return False

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
    # PayFast (South Africa — ITN / Instant Transaction Notification)
    # ------------------------------------------------------------------

    @classmethod
    def verify_payfast(cls, form: dict[str, str]) -> bool:
        """
        Verify PayFast ITN signature + merchant_id.

        PayFast posts form-encoded ITN bodies; signature is MD5 of the
        form-encoded params (insertion order, excluding 'signature'),
        plus '&passphrase=<url-encoded>' when a passphrase is configured.

        Dev-bypass when PAYFAST_MERCHANT_ID is unset or placeholder
        (mirrors verify_paystack behaviour for local smoke tests).
        """
        from urllib.parse import quote_plus

        merchant_id = os.environ.get("PAYFAST_MERCHANT_ID", "")
        if not merchant_id or cls._is_placeholder(merchant_id):
            return True

        if form.get("merchant_id", "") != merchant_id:
            _log.warning("PayFast ITN rejected: merchant_id mismatch")
            return False

        supplied = form.get("signature", "")
        if not supplied:
            return False

        parts = [f"{k}={quote_plus(str(v))}" for k, v in form.items() if k != "signature"]
        sig_string = "&".join(parts)

        passphrase = os.environ.get("PAYFAST_PASSPHRASE", "")
        if passphrase and not cls._is_placeholder(passphrase):
            sig_string += f"&passphrase={quote_plus(passphrase)}"

        expected = hashlib.md5(sig_string.encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected, supplied.lower())

    @staticmethod
    def parse_payfast(form: dict[str, str]) -> dict[str, Any] | None:
        """Parse PayFast ITN. Only COMPLETE payments become PaymentEvents."""
        if form.get("payment_status") != "COMPLETE":
            return None
        try:
            amount = float(form.get("amount_gross", "0"))
        except (TypeError, ValueError):
            return None
        return {
            "rail": "payfast",
            "type": "payment",
            "amount": amount,
            "currency": "ZAR",
            "customer": form.get("email_address", ""),
            "reference": form.get("pf_payment_id", "") or form.get("m_payment_id", ""),
            "plan": form.get("custom_str1", ""),
            "meta": {
                "m_payment_id": form.get("m_payment_id", ""),
                "item_name": form.get("item_name", ""),
            },
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
