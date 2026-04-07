"""TVM auth stub — wire to bridgeos.identity / JWT later."""
from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

from app.domains.tvm.models import TVMPrincipal


def _testing_mode() -> bool:
    return bool(os.environ.get("BRIDGE_TESTING") or os.environ.get("PYTEST_CURRENT_TEST"))


def _dev_headers_allowed() -> bool:
    v = os.environ.get("BRIDGE_TVM_DEV_HEADERS", "").lower()
    return v in ("1", "true", "yes")


def get_tvm_principal(request: Request) -> TVMPrincipal:
    """
    Resolve principal for TVM routes.

    - Tests / optional dev: ``X-TVM-Roles`` comma-separated (e.g. ``tvm.operator``).
    - Service: ``Authorization: Bearer <BRIDGE_INTERNAL_SECRET>`` → ``tvm.system``.
    """
    if _testing_mode() or _dev_headers_allowed():
        hdr = request.headers.get("X-TVM-Roles", "")
        if hdr.strip():
            roles = [r.strip() for r in hdr.split(",") if r.strip()]
            name = request.headers.get("X-TVM-Principal-Name", "dev")
            return TVMPrincipal(name=name, roles=roles)

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        internal = os.environ.get("BRIDGE_INTERNAL_SECRET", "")
        if internal and hmac.compare_digest(token, internal):
            return TVMPrincipal(name="bridgeos.system", roles=["tvm.system"])

    raise HTTPException(
        status_code=401,
        detail="TVM auth required: X-TVM-Roles (dev/test), or Bearer BRIDGE_INTERNAL_SECRET for tvm.system",
    )


def require_any_role(principal: TVMPrincipal, allowed: list[str]) -> None:
    if not any(r in principal.roles for r in allowed):
        raise HTTPException(status_code=403, detail="Forbidden: insufficient TVM role")
