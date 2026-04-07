"""
SIWE Auth — Sovereign Web3 Entry Protocol

Backend signature verification, replay protection (nonce DB), JWT issuance.
Optional: on-chain role verification before login approval.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any

import jwt
from eth_account import Account
from eth_account.messages import encode_defunct

# Config — JWT secret MUST be set to a strong value. No insecure fallbacks.
_INSECURE_PLACEHOLDERS = {"change-me-in-production", "change-me", "secret", "placeholder", ""}
JWT_SECRET = os.environ.get("BRIDGE_SIWE_JWT_SECRET", "")
if JWT_SECRET.lower().strip() in _INSECURE_PLACEHOLDERS or len(JWT_SECRET) < 32:
    import warnings
    warnings.warn(
        "BRIDGE_SIWE_JWT_SECRET is missing, too short (<32 chars), or set to an insecure placeholder. "
        "JWT signing/verification will FAIL. Generate one with: python -c \"import secrets; print(secrets.token_hex(64))\"",
        stacklevel=1,
    )
    # In production, crash hard. In dev, warn but allow startup with a random ephemeral secret.
    _env = os.environ.get("ENV", os.environ.get("BRIDGE_ENV", os.environ.get("NODE_ENV", ""))).lower()
    if _env == "production":
        raise RuntimeError(
            "CRITICAL: BRIDGE_SIWE_JWT_SECRET must be set to a strong secret (>=32 chars) in production. "
            "Refusing to start with an insecure or missing secret."
        )
    import secrets as _secrets
    JWT_SECRET = _secrets.token_hex(64)  # Ephemeral — all tokens invalidated on restart

JWT_EXPIRY_SEC = int(os.environ.get("BRIDGE_SIWE_JWT_EXPIRY", "86400"))  # 24h
_default_siwe_domains = ",".join([
    "localhost", "localhost:3020", "localhost:3021", "127.0.0.1",
    # Production / Vercel — always allowed without env override
    "go.ai-os.co.za",
    "app.ai-os.co.za",
    "ai-os.co.za",
    "bridge-live-wall.vercel.app",
    "bridge-ai-os.com",
])
ALLOWED_DOMAINS = [
    d.strip().lower()
    for d in os.environ.get("BRIDGE_SIWE_ALLOWED_DOMAINS", _default_siwe_domains).split(",")
    if d.strip()
]
REQUIRE_ONCHAIN_ROLE = os.environ.get("BRIDGE_SIWE_REQUIRE_ROLE", "0") == "1"
ROLE_CONTRACT = os.environ.get("BRIDGE_SIWE_ROLE_CONTRACT", "")
RPC_URL = os.environ.get("BRIDGE_SIWE_RPC_URL", "https://rpc.linea.build")
CHAIN_ID = int(os.environ.get("BRIDGE_SIWE_CHAIN_ID", "59144"))

# Message format from gateway: "Bridge AI OS Login\nDomain: X\nAddress: 0x...\nNonce: 123"
MSG_PATTERN = re.compile(
    r"Bridge AI OS Login\s+Domain:\s*(.+?)\s+Address:\s*(0x[a-fA-F0-9]{40})\s+Nonce:\s*([a-fA-F0-9]+)",
    re.DOTALL,
)


def parse_siwe_message(message: str) -> tuple[str, str, str] | None:
    """Parse (domain, address, nonce) from SIWE-style message. Returns None if invalid."""
    m = MSG_PATTERN.search(message.strip())
    if not m:
        return None
    domain, address, nonce = m.group(1).strip(), m.group(2).lower(), m.group(3)
    return domain, address, nonce


def verify_signature(message: str, signature: str) -> str | None:
    """Recover signer address from message + signature. Returns address or None."""
    try:
        msg_hash = encode_defunct(text=message)
        acct = Account.recover_message(msg_hash, signature=signature)
        return acct.lower() if acct else None
    except Exception:
        return None


def verify_domain(domain: str) -> bool:
    """Check domain is in allowed list."""
    d = domain.lower().strip()
    return d in ALLOWED_DOMAINS


def create_jwt(address: str, authority: str = "economic") -> str:
    """Issue JWT for authenticated address."""
    payload = {
        "sub": address,
        "auth": authority,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY_SEC,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt(token: str) -> dict | None:
    """Verify JWT and return payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        return None


def nonce_key(address: str, nonce: str) -> str:
    return f"siwe:nonce:{address}:{nonce}"


async def is_nonce_used(memory: Any, address: str, nonce: str) -> bool:
    """Check if nonce was already used (replay protection)."""
    key = nonce_key(address, nonce)
    val = await memory.get(key)
    return val is not None


async def store_nonce_used(memory: Any, address: str, nonce: str, ttl_sec: int = 86400 * 7) -> None:
    """Mark nonce as used. TTL 7 days."""
    key = nonce_key(address, nonce)
    if memory._r:
        await memory._r.setex(key, ttl_sec, "1")


async def verify_onchain_role(address: str) -> bool:
    """Check if address has role on-chain. Returns True if no role contract configured."""
    if not ROLE_CONTRACT or not REQUIRE_ONCHAIN_ROLE:
        return True
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        role_hex = os.environ.get("BRIDGE_SIWE_ROLE_HASH", "0x0000000000000000000000000000000000000000000000000000000000000000")
        role_bytes = bytes.fromhex(role_hex[2:].replace("0x", "").zfill(64))
        role_abi = [{"inputs": [{"type": "bytes32"}, {"type": "address"}], "name": "hasRole", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"}]
        contract = w3.eth.contract(address=Web3.to_checksum_address(ROLE_CONTRACT), abi=role_abi)
        has_role = contract.functions.hasRole(role_bytes, Web3.to_checksum_address(address)).call()
        return bool(has_role)
    except Exception:
        return False
