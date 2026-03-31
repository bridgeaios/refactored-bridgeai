"""FastAPI Depends() factories for the infra domain."""
from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domains.infra.services import InfraServices

_singleton: InfraServices | None = None
_bearer = HTTPBearer(auto_error=False)

# Internal service token — read lazily at request time so that env vars
# populated by _load_twin_env() in main.py (which runs after module imports)
# are visible. Set BRIDGE_INTERNAL_TOKEN in .env to a strong random secret.
def _internal_token() -> str:
    return os.environ.get("BRIDGE_INTERNAL_TOKEN", "")


def get_infra() -> InfraServices:
    """Return the singleton InfraServices instance."""
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory
        _singleton = InfraServices(memory=get_memory())
    return _singleton


def require_jwt(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:
    """Verify Bearer JWT from Authorization header or HttpOnly cookie.
    Accepts:
    - Authorization: Bearer <JWT> header
    - access_token cookie (HttpOnly, set after /auth/login)
    - BRIDGE_INTERNAL_TOKEN (internal machine-to-machine service calls)
    """
    from app.services.siwe_auth import verify_jwt

    # Get token from Authorization header first
    token = credentials.credentials if credentials else None

    # Fall back to HttpOnly cookie if no Authorization header
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Fast-path: internal service token (constant-time compare)
    import hmac
    _tok = _internal_token()
    if _tok and hmac.compare_digest(token, _tok):
        return {"sub": "internal-service", "authority": "internal"}

    # Standard SIWE JWT path
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload
