"""
KeyForge — Deterministic Rotating Key System
=============================================

A stateless distributed authentication layer using HMAC-based key derivation
with time-based epochs, scoped contexts, rolling entropy, and zero-trust
validation.

Architecture:
  Master Secret → HKDF → Epoch Key → HMAC(scope + epoch + chain) → Derived Key

  Any node with the same master secret + clock derives identical keys.
  No centralized storage required for validation.

Properties:
  - Deterministic: same inputs → same key on every node
  - Rotating: keys change every epoch (default 10 min)
  - Scoped: per-service, per-domain, per-channel isolation
  - Chained: each epoch incorporates previous epoch's entropy
  - Revocable: key IDs can be disabled in real-time via broadcast
  - Auditable: version + epoch + scope embedded in every token
  - Drift-tolerant: validates current + previous + next epoch (grace window)
  - Timing-safe: constant-time comparison for all validation

Usage:
  forge = KeyForge.from_env()          # Load from environment
  token = forge.issue("api-gateway")   # Issue scoped token
  result = forge.validate(token)       # Validate on any node
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# =============================================================================
# Constants
# =============================================================================

EPOCH_DURATION_SEC = int(os.environ.get("KEYFORGE_EPOCH_SEC", "600"))  # 10 min
DRIFT_TOLERANCE_EPOCHS = int(os.environ.get("KEYFORGE_DRIFT_EPOCHS", "1"))
KEY_VERSION = 2  # Bump on algorithm change — old tokens rejected
TOKEN_PREFIX = "kf2."  # Version-tagged prefix for tokens
MAX_TOKEN_AGE_SEC = EPOCH_DURATION_SEC * (DRIFT_TOLERANCE_EPOCHS + 1) * 2
CHAIN_LOOKBACK = 3  # How many previous epochs feed into rolling entropy


class KeyScope(str, Enum):
    """Pre-defined scopes for isolation. Extend as needed."""
    API_GATEWAY = "api-gateway"
    INTERNAL = "internal"
    ORCHESTRATOR = "orchestrator"
    ECONOMIC = "economic"
    WEBSOCKET = "websocket"
    AGENT = "agent"
    WEBHOOK = "webhook"
    ADMIN = "admin"


# =============================================================================
# Master Secret Derivation — Multi-source entropy, no single point of failure
# =============================================================================

def _derive_master_secret() -> bytes:
    """
    Derive master secret from multiple entropy sources.
    If KEYFORGE_MASTER is set, use it directly (for multi-node sync).
    Otherwise, derive from all available BRIDGE secrets + machine entropy.

    Returns 64-byte master secret.
    """
    explicit = os.environ.get("KEYFORGE_MASTER", "").strip()
    if explicit and len(explicit) >= 64:
        return hashlib.sha512(explicit.encode()).digest()

    # Combine all available entropy sources — survives partial env loss
    sources = []

    # Primary secrets
    for key in (
        "BRIDGE_SIWE_JWT_SECRET",
        "BRIDGE_INTERNAL_SECRET",
        "BRIDGE_ORCHESTRATOR_SECRET",
        "JWT_SECRET",
        "JWT_SECRET_KEY",
    ):
        val = os.environ.get(key, "")
        if val and len(val) >= 16:
            sources.append(val)

    if not sources:
        raise RuntimeError(
            "KEYFORGE: No entropy sources found. Set KEYFORGE_MASTER or at least "
            "one of BRIDGE_SIWE_JWT_SECRET, BRIDGE_INTERNAL_SECRET, JWT_SECRET."
        )

    # Machine-specific salt (stable across restarts, unique per host)
    machine_id = _get_machine_id()
    sources.append(machine_id)

    # HKDF-like derivation: combine sources with domain separation
    combined = b""
    for i, src in enumerate(sources):
        combined += hmac.new(
            key=f"keyforge-source-{i}".encode(),
            msg=src.encode() if isinstance(src, str) else src,
            digestmod=hashlib.sha256,
        ).digest()

    # Final extraction via HKDF-Extract
    prk = hmac.new(
        key=b"keyforge-v2-extract",
        msg=combined,
        digestmod=hashlib.sha512,
    ).digest()

    return prk


def _get_machine_id() -> str:
    """Stable machine identifier. Falls back gracefully."""
    # Linux
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            mid = Path(path).read_text().strip()
            if mid:
                return mid
        except (OSError, PermissionError):
            pass
    # Windows
    try:
        import subprocess
        result = subprocess.run(
            ["wmic", "csproduct", "get", "UUID"],
            capture_output=True, text=True, timeout=5,
        )
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip() and l.strip() != "UUID"]
        if lines:
            return lines[0]
    except Exception:
        pass
    # Fallback: hostname + username (weak but stable)
    import socket
    return f"{socket.gethostname()}:{os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))}"


# =============================================================================
# Epoch Computation
# =============================================================================

def current_epoch(now: float | None = None) -> int:
    """Current epoch number (unix timestamp // duration)."""
    return int((now or time.time()) // EPOCH_DURATION_SEC)


def epoch_range(center_epoch: int, tolerance: int = DRIFT_TOLERANCE_EPOCHS) -> list[int]:
    """Return valid epochs: [center - tolerance, ..., center + tolerance]."""
    return list(range(center_epoch - tolerance, center_epoch + tolerance + 1))


# =============================================================================
# Key Derivation — Deterministic, scoped, chained
# =============================================================================

def _derive_epoch_key(master: bytes, epoch: int) -> bytes:
    """Derive a per-epoch key from master secret."""
    return hmac.new(
        key=master,
        msg=f"keyforge-epoch-{KEY_VERSION}-{epoch}".encode(),
        digestmod=hashlib.sha256,
    ).digest()


def _rolling_entropy(master: bytes, epoch: int, lookback: int = CHAIN_LOOKBACK) -> bytes:
    """
    Rolling entropy: chain previous epoch keys into current derivation.
    Prevents predictability even if an attacker observes N consecutive tokens.
    """
    chain = b""
    for i in range(lookback):
        prev_epoch = epoch - i - 1
        if prev_epoch < 0:
            continue
        chain += _derive_epoch_key(master, prev_epoch)
    if not chain:
        chain = b"\x00" * 32
    return hashlib.sha256(chain).digest()


def derive_key(
    master: bytes,
    epoch: int,
    scope: str,
    *,
    key_id: str = "default",
) -> bytes:
    """
    Derive a scoped, chained key for a specific epoch.

    derivation = HMAC-SHA256(
        key = epoch_key,
        msg = version || scope || key_id || rolling_entropy
    )
    """
    epoch_key = _derive_epoch_key(master, epoch)
    entropy = _rolling_entropy(master, epoch)

    msg = struct.pack(">H", KEY_VERSION)  # 2-byte version
    msg += scope.encode().ljust(64, b"\x00")[:64]  # Fixed-width scope
    msg += key_id.encode().ljust(32, b"\x00")[:32]  # Fixed-width key_id
    msg += entropy  # 32-byte rolling entropy

    return hmac.new(
        key=epoch_key,
        msg=msg,
        digestmod=hashlib.sha256,
    ).digest()


# =============================================================================
# Token Format — Compact, self-describing, verifiable
# =============================================================================

@dataclass
class KeyForgeToken:
    """Serializable token structure."""
    version: int
    epoch: int
    scope: str
    key_id: str
    issued_at: float
    signature: str  # hex-encoded HMAC

    def serialize(self) -> str:
        """Compact wire format: kf2.<base64(json)>.<signature>"""
        import base64
        payload = {
            "v": self.version,
            "e": self.epoch,
            "s": self.scope,
            "k": self.key_id,
            "t": self.issued_at,
        }
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
        return f"{TOKEN_PREFIX}{payload_b64}.{self.signature}"

    @classmethod
    def deserialize(cls, raw: str) -> KeyForgeToken | None:
        """Parse token string. Returns None if malformed."""
        import base64
        if not raw.startswith(TOKEN_PREFIX):
            return None
        body = raw[len(TOKEN_PREFIX):]
        parts = body.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        # Restore base64 padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        try:
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes)
        except Exception:
            return None
        return cls(
            version=payload.get("v", 0),
            epoch=payload.get("e", 0),
            scope=payload.get("s", ""),
            key_id=payload.get("k", "default"),
            issued_at=payload.get("t", 0),
            signature=sig,
        )


def _sign_token_payload(master: bytes, epoch: int, scope: str, key_id: str, issued_at: float) -> str:
    """Compute HMAC signature for token payload."""
    derived = derive_key(master, epoch, scope, key_id=key_id)
    msg = f"{KEY_VERSION}:{epoch}:{scope}:{key_id}:{issued_at:.3f}".encode()
    return hmac.new(key=derived, msg=msg, digestmod=hashlib.sha256).hexdigest()


# =============================================================================
# Validation Result
# =============================================================================

@dataclass
class ValidationResult:
    valid: bool
    scope: str = ""
    key_id: str = ""
    epoch: int = 0
    reason: str = ""
    drift_epochs: int = 0  # How many epochs off from current


# =============================================================================
# Revocation — In-memory set, propagated via broadcast
# =============================================================================

class RevocationRegistry:
    """
    Tracks revoked key_ids and scopes. In-memory for speed.
    Propagated across nodes via WebSocket broadcast or Redis pub/sub.
    """

    def __init__(self) -> None:
        self._revoked_keys: set[str] = set()
        self._revoked_scopes: set[str] = set()
        self._revoked_at: dict[str, float] = {}

    def revoke_key(self, key_id: str) -> None:
        self._revoked_keys.add(key_id)
        self._revoked_at[f"key:{key_id}"] = time.time()

    def revoke_scope(self, scope: str) -> None:
        self._revoked_scopes.add(scope)
        self._revoked_at[f"scope:{scope}"] = time.time()

    def reinstate_key(self, key_id: str) -> None:
        self._revoked_keys.discard(key_id)
        self._revoked_at.pop(f"key:{key_id}", None)

    def reinstate_scope(self, scope: str) -> None:
        self._revoked_scopes.discard(scope)
        self._revoked_at.pop(f"scope:{scope}", None)

    def is_revoked(self, key_id: str, scope: str) -> bool:
        return key_id in self._revoked_keys or scope in self._revoked_scopes

    def export_state(self) -> dict:
        """Export for broadcast to other nodes."""
        return {
            "revoked_keys": sorted(self._revoked_keys),
            "revoked_scopes": sorted(self._revoked_scopes),
            "revoked_at": dict(self._revoked_at),
        }

    def import_state(self, state: dict) -> None:
        """Merge state from another node (union merge — revocations are sticky)."""
        self._revoked_keys |= set(state.get("revoked_keys", []))
        self._revoked_scopes |= set(state.get("revoked_scopes", []))
        for k, v in state.get("revoked_at", {}).items():
            if k not in self._revoked_at or v > self._revoked_at[k]:
                self._revoked_at[k] = v


# =============================================================================
# KeyForge — Main System
# =============================================================================

class KeyForge:
    """
    Deterministic rotating key system.

    Usage:
        forge = KeyForge.from_env()
        token = forge.issue("api-gateway")
        result = forge.validate(token)
        assert result.valid
    """

    def __init__(self, master: bytes, active_keys: set[str] | None = None):
        self._master = master
        self._active_keys: set[str] = active_keys or {"default"}
        self._revocations = RevocationRegistry()
        self._audit_log: list[dict] = []
        self._boot_epoch = current_epoch()

        # Verify determinism on init
        self._self_test()

    @classmethod
    def from_env(cls) -> KeyForge:
        """Create KeyForge from environment variables."""
        master = _derive_master_secret()
        active = os.environ.get("KEYFORGE_ACTIVE_KEYS", "default")
        active_set = {k.strip() for k in active.split(",") if k.strip()}
        return cls(master=master, active_keys=active_set)

    @classmethod
    def from_secret(cls, secret: str) -> KeyForge:
        """Create KeyForge from an explicit secret string."""
        if len(secret) < 32:
            raise ValueError("Secret must be at least 32 characters")
        master = hashlib.sha512(secret.encode()).digest()
        return cls(master=master)

    def _self_test(self) -> None:
        """Verify key derivation is deterministic."""
        epoch = self._boot_epoch
        k1 = derive_key(self._master, epoch, "selftest", key_id="test")
        k2 = derive_key(self._master, epoch, "selftest", key_id="test")
        if k1 != k2:
            raise RuntimeError("KEYFORGE: Determinism check failed — key derivation is non-deterministic")

    # ── Key Management ──────────────────────────────────────────────

    def add_key(self, key_id: str) -> None:
        """Enable a key ID for token issuance."""
        self._active_keys.add(key_id)
        self._audit("key_added", key_id=key_id)

    def remove_key(self, key_id: str) -> None:
        """Disable a key ID. Existing tokens with this ID become invalid."""
        self._active_keys.discard(key_id)
        self._revocations.revoke_key(key_id)
        self._audit("key_removed", key_id=key_id)

    def revoke_scope(self, scope: str) -> None:
        """Revoke all tokens for a scope. Propagate via broadcast."""
        self._revocations.revoke_scope(scope)
        self._audit("scope_revoked", scope=scope)

    def reinstate_scope(self, scope: str) -> None:
        self._revocations.reinstate_scope(scope)
        self._audit("scope_reinstated", scope=scope)

    @property
    def active_keys(self) -> set[str]:
        return set(self._active_keys)

    @property
    def revocations(self) -> RevocationRegistry:
        return self._revocations

    # ── Token Issuance ──────────────────────────────────────────────

    def issue(
        self,
        scope: str,
        *,
        key_id: str = "default",
        now: float | None = None,
    ) -> str:
        """
        Issue a token for the given scope.

        Args:
            scope: Service/domain scope (e.g., "api-gateway", "internal")
            key_id: Which key identity to use (must be in active_keys)
            now: Override current time (for testing)

        Returns:
            Serialized token string (kf2.xxxxx.signature)

        Raises:
            ValueError: If key_id is not active or scope is revoked
        """
        if key_id not in self._active_keys:
            raise ValueError(f"Key '{key_id}' is not active")
        if self._revocations.is_revoked(key_id, scope):
            raise ValueError(f"Key '{key_id}' or scope '{scope}' is revoked")

        ts = now or time.time()
        epoch = current_epoch(ts)
        sig = _sign_token_payload(self._master, epoch, scope, key_id, ts)

        token = KeyForgeToken(
            version=KEY_VERSION,
            epoch=epoch,
            scope=scope,
            key_id=key_id,
            issued_at=ts,
            signature=sig,
        )

        self._audit("token_issued", scope=scope, key_id=key_id, epoch=epoch)
        return token.serialize()

    # ── Token Validation ────────────────────────────────────────────

    def validate(
        self,
        raw_token: str,
        *,
        required_scope: str | None = None,
        now: float | None = None,
    ) -> ValidationResult:
        """
        Validate a token. Checks:
          1. Token format and version
          2. Revocation status
          3. Epoch validity (current ± drift tolerance)
          4. Age limit
          5. HMAC signature (constant-time comparison)
          6. Scope match (if required_scope specified)

        Returns ValidationResult with .valid bool and .reason on failure.
        """
        # Parse
        token = KeyForgeToken.deserialize(raw_token)
        if token is None:
            return ValidationResult(valid=False, reason="malformed_token")

        # Version check
        if token.version != KEY_VERSION:
            return ValidationResult(valid=False, reason=f"version_mismatch:{token.version}")

        # Revocation check
        if self._revocations.is_revoked(token.key_id, token.scope):
            return ValidationResult(valid=False, reason="revoked")

        # Epoch and time checks
        ts = now or time.time()
        cur_epoch = current_epoch(ts)
        valid_epochs = epoch_range(cur_epoch)

        if token.epoch not in valid_epochs:
            return ValidationResult(
                valid=False,
                reason="epoch_expired",
                epoch=token.epoch,
                drift_epochs=abs(token.epoch - cur_epoch),
            )

        # Age check — allow up to DRIFT_TOLERANCE epochs into the future for clock skew
        age = ts - token.issued_at
        max_future = EPOCH_DURATION_SEC * (DRIFT_TOLERANCE_EPOCHS + 1)
        if age > MAX_TOKEN_AGE_SEC or age < -max_future:
            return ValidationResult(valid=False, reason="token_too_old")

        # Scope match
        if required_scope and token.scope != required_scope:
            return ValidationResult(valid=False, reason=f"scope_mismatch:{token.scope}")

        # Signature verification — constant-time comparison
        expected_sig = _sign_token_payload(
            self._master, token.epoch, token.scope, token.key_id, token.issued_at,
        )
        if not hmac.compare_digest(expected_sig, token.signature):
            return ValidationResult(valid=False, reason="invalid_signature")

        drift = token.epoch - cur_epoch
        return ValidationResult(
            valid=True,
            scope=token.scope,
            key_id=token.key_id,
            epoch=token.epoch,
            drift_epochs=drift,
        )

    # ── Persistence ─────────────────────────────────────────────────

    def persist_state(self, path: str | Path) -> None:
        """
        Persist revocation state and active keys to disk.
        Master secret is NOT persisted — it's derived from env.
        """
        state = {
            "version": KEY_VERSION,
            "active_keys": sorted(self._active_keys),
            "revocations": self._revocations.export_state(),
            "persisted_at": time.time(),
            "epoch": current_epoch(),
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.replace(p)

    def restore_state(self, path: str | Path) -> bool:
        """Restore state from disk. Returns True if successful."""
        p = Path(path)
        if not p.exists():
            return False
        try:
            state = json.loads(p.read_text())
            if state.get("version") != KEY_VERSION:
                return False  # Don't load incompatible state
            self._active_keys = set(state.get("active_keys", ["default"]))
            self._revocations.import_state(state.get("revocations", {}))
            return True
        except Exception:
            return False

    # ── Sync — Merge state from another node ────────────────────────

    def merge_remote_state(self, remote_state: dict) -> None:
        """
        Merge state received from another KeyForge node.
        Revocations use union merge (sticky). Active keys use intersection
        (a key removed on any node is removed everywhere).
        """
        remote_keys = set(remote_state.get("active_keys", []))
        # Intersection: if a key was removed on the remote, respect that
        self._active_keys &= remote_keys
        self._revocations.import_state(remote_state.get("revocations", {}))
        self._audit("state_merged")

    def export_sync_state(self) -> dict:
        """Export state for broadcasting to other nodes."""
        return {
            "version": KEY_VERSION,
            "active_keys": sorted(self._active_keys),
            "revocations": self._revocations.export_state(),
            "node_epoch": current_epoch(),
        }

    # ── Audit ───────────────────────────────────────────────────────

    def _audit(self, action: str, **kwargs: Any) -> None:
        entry = {
            "action": action,
            "at": time.time(),
            "epoch": current_epoch(),
            **kwargs,
        }
        self._audit_log.append(entry)
        # Keep last 500 entries
        if len(self._audit_log) > 500:
            self._audit_log = self._audit_log[-500:]

    def get_audit_log(self) -> list[dict]:
        return list(self._audit_log)

    # ── Diagnostics ─────────────────────────────────────────────────

    def status(self) -> dict:
        """System status for health checks."""
        epoch = current_epoch()
        return {
            "version": KEY_VERSION,
            "epoch": epoch,
            "epoch_duration_sec": EPOCH_DURATION_SEC,
            "drift_tolerance": DRIFT_TOLERANCE_EPOCHS,
            "active_keys": sorted(self._active_keys),
            "revoked_keys": sorted(self._revocations._revoked_keys),
            "revoked_scopes": sorted(self._revocations._revoked_scopes),
            "boot_epoch": self._boot_epoch,
            "uptime_epochs": epoch - self._boot_epoch,
            "audit_entries": len(self._audit_log),
        }


# =============================================================================
# Singleton — Global instance
# =============================================================================

_instance: KeyForge | None = None


def get_keyforge() -> KeyForge:
    """Get or create the global KeyForge instance."""
    global _instance
    if _instance is None:
        _instance = KeyForge.from_env()
        # Try restoring persisted state
        state_path = Path(os.environ.get(
            "KEYFORGE_STATE_PATH",
            str(Path(__file__).parent.parent.parent / "data" / "keyforge-state.json"),
        ))
        _instance.restore_state(state_path)
    return _instance


def reset_instance() -> None:
    """Reset singleton (for testing)."""
    global _instance
    _instance = None
