"""
AUTH + MERKLE AUDIT — Tamper-evident auth ledger.

Every auth event (register / login / verify / token-check) is hashed as a
leaf and appended to an in-memory Merkle tree.  Altering any event changes
the root, making tampering detectable.

Routes (all under prefix /api):
  POST /auth/register          — create ephemeral account, issue JWT
  POST /auth/login             — email+password, issue JWT
  POST /auth/verify            — SIWE-compatible JWT verify
  POST /auth/verify-token      — inspect a raw Bearer token
  GET  /auth/audit/events      — list audit leaves
  GET  /auth/audit/root        — current root + integrity status
  POST /auth/audit/verify      — full integrity check
  GET  /auth/audit/proof/{hash}— Merkle proof for a leaf
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from app.domains.infra.deps import require_jwt

# ─── optional: import the project's JWT helpers ─────────────────────────────
try:
    from app.services.siwe_auth import create_jwt, verify_jwt  # type: ignore
except Exception:
    import jwt as _pyjwt

    _EPHEMERAL_SECRET = secrets.token_hex(32)

    def create_jwt(address: str, authority: str = "economic") -> str:  # type: ignore[misc]
        payload = {"sub": address, "auth": authority,
                   "iat": int(time.time()), "exp": int(time.time()) + 86400}
        return _pyjwt.encode(payload, _EPHEMERAL_SECRET, algorithm="HS256")

    def verify_jwt(token: str) -> dict | None:  # type: ignore[misc]
        try:
            return _pyjwt.decode(token, _EPHEMERAL_SECRET, algorithms=["HS256"])
        except Exception:
            return None


router = APIRouter(prefix="/auth", tags=["auth-merkle-audit"])

# ─── In-process user store (ephemeral — replace with DB for production) ──────
_users: dict[str, str] = {}   # email → hashed_password

# ─── Merkle Audit Log ────────────────────────────────────────────────────────

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def _leaf_hash(event_id: int, action: str, actor: str, ts: float) -> str:
    """Deterministic leaf: SHA256(id|action|actor|ts)"""
    return _sha256(f"{event_id}|{action}|{actor}|{ts:.6f}")


def _hash_pair(left: str, right: str) -> str:
    return _sha256(left + right)


def _compute_root(leaves: list[str]) -> str:
    if not leaves:
        return _sha256("empty")
    level = list(leaves)
    while len(level) > 1:
        nxt: list[str] = []
        for i in range(0, len(level), 2):
            l = level[i]
            r = level[i + 1] if i + 1 < len(level) else l  # duplicate last if odd
            nxt.append(_hash_pair(l, r))
        level = nxt
    return level[0]


def _merkle_proof(leaves: list[str], target: str) -> list[dict] | None:
    """Return sibling path from leaf → root. None if target not in leaves."""
    if target not in leaves:
        return None
    proof: list[dict] = []
    level = list(leaves)
    idx = level.index(target)
    while len(level) > 1:
        sib_idx = idx ^ 1
        if sib_idx < len(level):
            sib = level[sib_idx]
            pos = "right" if idx % 2 == 0 else "left"
        else:
            sib = level[idx]
            pos = "right"
        proof.append({"hash": sib, "position": pos})
        nxt: list[str] = []
        for i in range(0, len(level), 2):
            l = level[i]
            r = level[i + 1] if i + 1 < len(level) else l
            nxt.append(_hash_pair(l, r))
        level = nxt
        idx //= 2
    return proof


class _MerkleAuditLog:
    def __init__(self) -> None:
        self._events: list[dict] = []
        self._leaves: list[str] = []
        self._root: str = _sha256("empty")
        self._sealed_root: str = self._root   # root written at last verification

    def append(self, action: str, actor: str, meta: dict | None = None) -> dict:
        event_id = len(self._events) + 1
        ts = time.time()
        leaf = _leaf_hash(event_id, action, actor, ts)
        entry = {
            "id": event_id,
            "action": action,
            "actor": actor,
            "leaf_hash": leaf,
            "ts": ts,
            "meta": meta or {},
        }
        self._events.append(entry)
        self._leaves.append(leaf)
        self._root = _compute_root(self._leaves)
        self._sealed_root = self._root   # seal after every append
        return entry

    def root(self) -> str:
        return self._root

    def depth(self) -> int:
        n = len(self._leaves)
        if n == 0:
            return 0
        d = 0
        while (1 << d) < n:
            d += 1
        return d

    def check_integrity(self) -> bool:
        """Recompute root from stored leaves and compare to sealed root."""
        computed = _compute_root(self._leaves)
        return hmac.compare_digest(computed, self._sealed_root)

    def proof(self, leaf_hash: str) -> list[dict] | None:
        return _merkle_proof(self._leaves, leaf_hash)

    def events(self, limit: int = 100) -> list[dict]:
        return self._events[-limit:]


_audit = _MerkleAuditLog()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ─── AUTH ROUTES ─────────────────────────────────────────────────────────────

@router.post("/register")
async def register(
    email: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
) -> dict[str, Any]:
    if not email or "@" not in email:
        raise HTTPException(400, "Invalid email")
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if email in _users:
        raise HTTPException(409, "Email already registered")

    _users[email] = _hash_password(password)
    token = create_jwt(email, authority="user")
    event = _audit.append("register", email, {"method": "email"})
    return {
        "status": "registered",
        "token": token,
        "leaf_hash": event["leaf_hash"],
        "merkle_root": _audit.root(),
    }


@router.post("/login")
async def login(
    email: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
) -> dict[str, Any]:
    hashed = _hash_password(password)
    stored = _users.get(email)
    if not stored or not hmac.compare_digest(hashed, stored):
        _audit.append("login_fail", email, {"reason": "invalid credentials"})
        raise HTTPException(401, "Invalid credentials")

    token = create_jwt(email, authority="user")
    event = _audit.append("login", email, {"method": "email"})
    return {
        "status": "authenticated",
        "token": token,
        "leaf_hash": event["leaf_hash"],
        "merkle_root": _audit.root(),
    }


@router.post("/verify")
async def verify_siwe(
    message: str = Body(..., embed=True),
    signature: str = Body(..., embed=True),
) -> dict[str, Any]:
    """SIWE signature verification flow."""
    try:
        from app.services.siwe_auth import (
            parse_siwe_message,
            verify_signature,
            verify_domain,
        )
        parsed = parse_siwe_message(message)
        if not parsed:
            raise HTTPException(400, "Invalid SIWE message format")
        domain, address, nonce = parsed
        if not verify_domain(domain):
            raise HTTPException(403, f"Domain '{domain}' not allowed")
        signer = verify_signature(message, signature)
        if not signer or signer != address:
            _audit.append("verify_fail", address or "unknown",
                          {"reason": "signature mismatch"})
            raise HTTPException(401, "Signature verification failed")
        token = create_jwt(address, authority="economic")
        event = _audit.append("verify", address, {"domain": domain, "nonce": nonce})
        return {
            "status": "verified",
            "address": address,
            "token": token,
            "leaf_hash": event["leaf_hash"],
            "merkle_root": _audit.root(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"SIWE module unavailable: {e}") from e


@router.post("/verify-token")
async def verify_token(
    token: str = Body(..., embed=True),
) -> dict[str, Any]:
    """Inspect and verify a raw Bearer JWT."""
    payload = verify_jwt(token)
    if not payload:
        _audit.append("token_verify_fail", "anonymous", {"reason": "invalid token"})
        return {"valid": False, "error": "Invalid or expired token"}
    event = _audit.append("token_verify", payload.get("sub", "unknown"),
                          {"authority": payload.get("auth", payload.get("authority", ""))})
    return {
        "valid": True,
        "payload": payload,
        "leaf_hash": event["leaf_hash"],
        "merkle_root": _audit.root(),
    }


# ─── AUDIT ROUTES ─────────────────────────────────────────────────────────────

@router.get("/audit/root")
async def audit_root() -> dict[str, Any]:
    ok = _audit.check_integrity()
    return {
        "root": _audit.root(),
        "leaves": len(_audit._leaves),
        "depth": _audit.depth(),
        "integrity": "PASS" if ok else "FAIL",
    }


@router.post("/audit/verify")
async def audit_verify() -> dict[str, Any]:
    ok = _audit.check_integrity()
    return {
        "integrity": "PASS" if ok else "FAIL",
        "root": _audit.root(),
        "leaves": len(_audit._leaves),
        "depth": _audit.depth(),
        "message": "Audit log is intact." if ok
                   else "INTEGRITY MISMATCH — audit log may be tampered.",
    }


@router.get("/audit/events")
async def audit_events(limit: int = 50, _caller: dict = Depends(require_jwt)) -> dict[str, Any]:
    events = _audit.events(limit=min(limit, 200))
    return {
        "events": events,
        "root": _audit.root(),
        "total": len(_audit._leaves),
    }


@router.get("/audit/proof/{leaf_hash}")
async def audit_proof(leaf_hash: str) -> dict[str, Any]:
    if len(leaf_hash) != 64 or not all(c in "0123456789abcdef" for c in leaf_hash.lower()):
        raise HTTPException(400, "leaf_hash must be a 64-char hex string")
    proof = _audit.proof(leaf_hash)
    if proof is None:
        raise HTTPException(404, "Leaf not found in audit log")
    # Allow client-side root verification
    return {
        "leaf_hash": leaf_hash,
        "proof": proof,
        "root": _audit.root(),
        "depth": _audit.depth(),
    }
