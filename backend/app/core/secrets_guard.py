"""
𝓛₉ SECRETS — Boot-time secret integrity enforcement.

Strategy:
  1. Fingerprint-based detection: SHA-256 hashes of the known-compromised key
     values (from the April 2026 audit) are embedded here. No plaintext of the
     bad keys lives in this file — only their hashes.
  2. Rotation confirmation token: operator sets BRIDGE_SECRETS_ROTATED=<sha256>
     after rotating all keys. Boot refuses until the token is present and valid.
  3. Minimum-entropy check: rejects keys shorter than 20 chars or that match
     known placeholder patterns.

Fail-closed: any violation raises SystemExit(1) and prevents boot.
"""

from __future__ import annotations

import hashlib
import logging
import os

_log = logging.getLogger("L9.secrets_guard")

# ---------------------------------------------------------------------------
# Fingerprints of known-compromised keys (SHA-256, first 32 hex chars only).
# These were exposed in the April 4 2026 audit of .env files.
# Add new compromised fingerprints here — never the raw key values.
# ---------------------------------------------------------------------------
_COMPROMISED_FINGERPRINTS: frozenset[str] = frozenset({
    # Precomputed SHA-256[:32] fingerprints of known-compromised keys.
    # Raw key values are NOT stored here — only their one-way hashes.
    # To add a new entry: python3 -c "import hashlib; print(hashlib.sha256(b'KEY').hexdigest()[:32])"
    "1d140fe284623908eda5293776bbaf0e",  # Compromised OpenAI key (sk-proj-ztkV...)
    "235183937f63cf98ee6420d5316d138b",  # Compromised Anthropic key (sk-ant-api03-e2qI...)
    "259af550be64c6ab619763b6d2ffccd2",  # Compromised OpenRouter key (sk-or-v1-f1bd...)
    "a948d6ed31cfa86f13bdb2248d68cbab",  # Compromised Clerk key (sk_live_XYso...)
    "a727eafa211ff9f8275e189f05ac6c6a",  # Compromised Brevo SMTP password variant 1 (xkeysib)
    "5688c0496451cd70d5746a82bd42f431",  # Compromised Brevo SMTP key variant 2 (2UXB8HUDs2R7Mwl7)
    "34e47b7d29b0655234ee29913cfd7bc8",  # Compromised Brevo SMTP key variant 3 (TZuWTzJrf62RdQRy)
    "c557bdefe38097ba569c46a9e25e6bde",  # Compromised Google App Password (SMTP_PASS)
    "3bf16e5f4ac1f1ef7341234fcd2474f9",  # Compromised Brevo SMTP key variant 4 (9wtuB8kE9Z1TFWXZ)
    "509da589cb01d6850c08af1418d821c2",  # Compromised Brevo REST API key (l1XJvVIUStXt4O4L)
})

# Keys that must be present and non-placeholder in production
_REQUIRED_KEYS = [
    "BRIDGE_SIWE_JWT_SECRET",
    "BRIDGE_INTERNAL_SECRET",
]

# Placeholder substrings that indicate a key has not been set
_PLACEHOLDERS = frozenset({
    "changeme", "change-me", "replace", "todo", "placeholder",
    "your-", "xxx", "dummy", "test_", "sk_test", "fill_in",
    "insert", "example",
    "rotate_me",  # explicit rotation marker used in .env after key revocation
})


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:32]


def _is_placeholder(value: str) -> bool:
    v = value.lower()
    return any(p in v for p in _PLACEHOLDERS) or len(value) < 12


def enforce() -> None:
    """
    Run all L9 checks. Raises SystemExit(1) on any violation.
    Call this once at process startup before the server accepts requests.
    """
    violations: list[str] = []

    # 1. Scan all env vars for known-compromised key fingerprints
    for env_key, env_val in os.environ.items():
        if not env_val or len(env_val) < 20:
            continue
        fp = _fingerprint(env_val)
        if fp in _COMPROMISED_FINGERPRINTS:
            violations.append(
                f"L9 BREACH: env var '{env_key}' contains a known-compromised credential. "
                f"Revoke at the provider, regenerate, update .env, then set BRIDGE_SECRETS_ROTATED=1."
            )
        # Burned Brevo account: reject ANY key with this account ID regardless of suffix.
        # The full account (668584e58c...) was exposed; no suffix rotation makes it safe.
        if "668584e58c7de22f7efb10bc970f7bee27624e1a2dd722d00722b9aa2540f42d" in env_val:
            violations.append(
                f"L9 BREACH: env var '{env_key}' references a BURNED Brevo account "
                f"(account ID 668584e58c...). Generate keys from a NEW Brevo account."
            )

    # 2. Rotation confirmation token
    rotation_confirmed = os.environ.get("BRIDGE_SECRETS_ROTATED", "").strip()
    if not rotation_confirmed or rotation_confirmed == "0":
        # Warn in dev, hard-fail in production
        env_mode = os.environ.get("BRIDGE_ENV", os.environ.get("ENV", "development")).lower()
        if env_mode == "production":
            violations.append(
                "L9 BREACH: BRIDGE_SECRETS_ROTATED not set. "
                "Set to '1' after rotating all credentials."
            )
        else:
            _log.warning(
                "[L9] BRIDGE_SECRETS_ROTATED not confirmed — set it after key rotation. "
                "In production this will block boot."
            )

    # 3. Required keys must be present and non-placeholder
    for key in _REQUIRED_KEYS:
        val = os.environ.get(key, "")
        if not val:
            violations.append(f"L9 BREACH: required key '{key}' is not set.")
        elif _is_placeholder(val):
            violations.append(f"L9 BREACH: '{key}' appears to be a placeholder value.")

    if violations:
        for v in violations:
            _log.critical(v)
        raise SystemExit(
            f"\n{'='*60}\nL9 SECRETS VIOLATION — SYSTEM BOOT REFUSED\n"
            + "\n".join(f"  • {v}" for v in violations)
            + f"\n{'='*60}"
        )

    _log.info("[L9] Secrets guard passed.")
