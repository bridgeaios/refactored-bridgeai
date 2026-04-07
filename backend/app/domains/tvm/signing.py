"""Row signing: HMAC-SHA256 over canonical JSON (excludes signature). Secret: BRIDGE_TVM_SIGNING_KEY or BRIDGE_INTERNAL_SECRET."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any


def _signing_key_bytes() -> bytes:
    key = os.environ.get("BRIDGE_TVM_SIGNING_KEY") or os.environ.get("BRIDGE_INTERNAL_SECRET") or ""
    if not key:
        # Dev/test only — L9 may still require INTERNAL_SECRET in production
        key = "dev-tvm-signing-key-change-in-production-min-32-chars!!"
    return key.encode("utf-8")


def canonical_json_bytes(row: dict[str, Any]) -> bytes:
    clean = {k: v for k, v in sorted(row.items()) if k != "signature" and v is not None}
    return json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_row(row: dict[str, Any]) -> str:
    payload = canonical_json_bytes(row)
    return hmac.new(_signing_key_bytes(), payload, hashlib.sha256).hexdigest()


def verify_row(row: dict[str, Any]) -> bool:
    sig = row.get("signature")
    if not sig or not isinstance(sig, str):
        return False
    expected = sign_row(row)
    return hmac.compare_digest(expected, sig)
