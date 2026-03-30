"""FastAPI Depends() factories for the infra domain."""
from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domains.infra.services import InfraServices

_singleton: InfraServices | None = None
_bearer = HTTPBearer(auto_error=False)

# Internal service token — used by workers.py and background tasks to call
# JWT-protected endpoints without a full SIWE login round-trip.
# Set BRIDGE_INTERNAL_TOKEN in .env to a strong random secret.
_INTERNAL_TOKEN: str = os.environ.get("BRIDGE_INTERNAL_TOKEN", "")


def get_infra() -> InfraServices:
    """Return the singleton InfraServices instance."""
    global _singleton
    if _singleton is None:
        from app.core.deps import get_memory
        _singleton = InfraServices(memory=get_memory())
    return _singleton


def require_jwt(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:
    """Verify Bearer JWT or internal service token.
    Accepts:
    - SIWE-issued JWT (validated via verify_jwt)
    - BRIDGE_INTERNAL_TOKEN (internal machine-to-machine service calls)
    """
    from app.services.siwe_auth import verify_jwt
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    # Fast-path: internal service token (constant-time compare)
    import hmac
    if _INTERNAL_TOKEN and hmac.compare_digest(token, _INTERNAL_TOKEN):
        return {"sub": "internal-service", "authority": "internal"}
    # Standard SIWE JWT path
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload
