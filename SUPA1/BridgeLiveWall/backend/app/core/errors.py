"""
Domain exception hierarchy for Bridge AI OS.

Every error raised in a domain package is a BridgeError subclass.
The global FastAPI exception handler converts all BridgeError subclasses
to a consistent { ok, code, message } JSON response.
"""
from __future__ import annotations


class BridgeError(Exception):
    """Base class for all Bridge AI OS domain errors."""

    code: str = "BRIDGE_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(BridgeError):
    """Resource not found — maps to HTTP 404."""

    code = "NOT_FOUND"


class ValidationError(BridgeError):
    """Input validation failed — maps to HTTP 422."""

    code = "VALIDATION_ERROR"


class EconomicGateError(BridgeError):
    """Execution gate rejected task — maps to HTTP 402."""

    code = "ECONOMIC_GATE_ERROR"


class AuthError(BridgeError):
    """Authentication or authorisation failure — maps to HTTP 401/403."""

    code = "AUTH_ERROR"


class NetworkError(BridgeError):
    """Swarm/replication/network failure — maps to HTTP 503."""

    code = "NETWORK_ERROR"


def error_response(exc: BridgeError) -> dict:
    """Convert a BridgeError to the canonical API error shape."""
    return {
        "ok": False,
        "code": exc.code,
        "message": exc.message,
    }
