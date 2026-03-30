"""FastAPI Depends() factories for the infra domain."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domains.infra.services import InfraServices

_singleton: InfraServices | None = None

_bearer = HTTPBearer(auto_error=False)


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
    """Verify Bearer JWT — raises 401 if missing or invalid."""
    from app.services.siwe_auth import verify_jwt
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload
