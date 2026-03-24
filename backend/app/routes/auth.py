"""
SIWE Auth Routes — Backend signature verification, nonce replay protection, JWT issuance.
"""
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.cortex import wrap_response
from app.services.siwe_auth import (
    create_jwt,
    is_nonce_used,
    parse_siwe_message,
    store_nonce_used,
    verify_domain,
    verify_onchain_role,
    verify_signature,
)

router = APIRouter()


class SiweLoginRequest(BaseModel):
    message: str
    signature: str


@router.post("/auth/siwe")
async def siwe_login(req: SiweLoginRequest, request: Request) -> dict[str, Any]:
    """
    SIWE login: verify signature, check nonce (replay protection), optionally verify on-chain role, issue JWT.
    """
    from app.main import memory

    message = req.message.strip()
    signature = req.signature.strip()
    if not message or not signature:
        raise HTTPException(status_code=400, detail="message and signature required")

    parsed = parse_siwe_message(message)
    if not parsed:
        raise HTTPException(status_code=400, detail="invalid message format")

    domain, claimed_address, nonce = parsed
    if not verify_domain(domain):
        raise HTTPException(status_code=403, detail="domain not allowed")

    recovered = verify_signature(message, signature)
    if not recovered or recovered != claimed_address.lower():
        raise HTTPException(status_code=401, detail="signature verification failed")

    if await is_nonce_used(memory, claimed_address, nonce):
        raise HTTPException(status_code=401, detail="nonce already used (replay)")

    if not await verify_onchain_role(claimed_address):
        raise HTTPException(status_code=403, detail="on-chain role verification failed")

    await store_nonce_used(memory, claimed_address, nonce)

    token = create_jwt(claimed_address, authority="economic")
    return wrap_response(
        {"token": token, "address": claimed_address, "auth": "economic"},
        ok=True,
    )
