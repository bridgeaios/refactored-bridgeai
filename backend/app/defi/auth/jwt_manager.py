"""
JWT manager — access (15 min) + refresh (7 day) with rotation and revocation.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

_SECRET = os.environ.get("DEFI_JWT_SECRET", "")
if not _SECRET or len(_SECRET) < 32:
    _env = os.environ.get("ENV", os.environ.get("BRIDGE_ENV", "")).lower()
    if _env == "production":
        raise RuntimeError(
            "CRITICAL: DEFI_JWT_SECRET must be set to a strong secret (>=32 chars) in production. "
            "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    import warnings as _w
    _w.warn(
        "DEFI_JWT_SECRET is missing or too short — using ephemeral secret. "
        "All DeFi sessions will be invalidated on restart. Set DEFI_JWT_SECRET in .env.",
        stacklevel=1,
    )
    _SECRET = secrets.token_hex(32)
_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = 15
_REFRESH_EXPIRE_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int, tier: str, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "tier": tier,
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=_ACCESS_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """Return (raw_token, family_id). Store hash(raw_token) in DB."""
    raw = secrets.token_urlsafe(64)
    family = str(uuid.uuid4())
    return raw, family


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict:
    """
    Decode and validate access token.
    Raises jwt.ExpiredSignatureError, jwt.InvalidTokenError on failure.
    """
    payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload


def refresh_token_expires_at() -> datetime:
    return _now() + timedelta(days=_REFRESH_EXPIRE_DAYS)
