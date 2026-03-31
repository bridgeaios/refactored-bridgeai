import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ── CSRF Protection Middleware ────────────────────────────────────────────────
class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF token protection for state-changing requests (POST, PUT, DELETE, PATCH).

    Generates a unique token per session and validates it on mutations.
    Token stored in secure, httpOnly cookie. Validated via X-CSRF-Token header or form field.
    """

    COOKIE_NAME = "_csrf_token"
    HEADER_NAME = "X-CSRF-Token"
    FORM_FIELD = "csrf_token"

    # Exempt paths from CSRF validation (GET, HEAD, OPTIONS always exempt)
    EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/openapi",
        "/public",
        "/ws",
    }

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF validation."""
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        return False

    def _generate_token(self) -> str:
        """Generate a cryptographically secure CSRF token."""
        return secrets.token_urlsafe(32)

    def _validate_token(self, provided: str, stored: str) -> bool:
        """
        Validate token using constant-time comparison.
        Uses hmac.compare_digest to prevent timing attacks.
        """
        if not provided or not stored:
            return False
        # Constant-time comparison — prevents timing attacks
        return hmac.compare_digest(provided, stored)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method

        # Safe methods: GET, HEAD, OPTIONS never require CSRF
        if method in ("GET", "HEAD", "OPTIONS"):
            response = await call_next(request)
            # Ensure token is in response for safe methods (for forms)
            self._set_csrf_cookie(response)
            return response  # type: ignore[no-any-return]

        # Exempt paths (health checks, docs, etc.)
        if self._is_exempt(path):
            return await call_next(request)  # type: ignore[no-any-return]

        # State-changing methods (POST, PUT, DELETE, PATCH): require CSRF validation
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            # Get stored token from cookie
            stored_token = request.cookies.get(self.COOKIE_NAME, "")

            if not stored_token:
                # No CSRF token in session — this is a fresh request, generate one
                response = Response(status_code=403, content="CSRF token missing")
                self._set_csrf_cookie(response)
                return response

            # Get provided token from header or form
            provided_token = request.headers.get(self.HEADER_NAME, "")

            # If header not present, try form data
            if not provided_token and method in ("POST", "PUT", "PATCH"):
                try:
                    # Read body once
                    body = await request.body()
                    if body:
                        # Try JSON
                        try:
                            data = json.loads(body)
                            provided_token = data.get(self.FORM_FIELD, "")
                        except (json.JSONDecodeError, ValueError):
                            # Try form-encoded
                            from urllib.parse import parse_qs
                            parsed = parse_qs(body.decode())
                            provided_token = parsed.get(self.FORM_FIELD, [""])[0]
                except Exception:
                    pass  # Continue with validation attempt

            # Validate token
            if not self._validate_token(provided_token, stored_token):
                return Response(status_code=403, content="Invalid CSRF token")

        # Request is valid, proceed
        response = await call_next(request)

        # Ensure token is refreshed in response
        self._set_csrf_cookie(response)
        return response  # type: ignore[no-any-return]

    def _set_csrf_cookie(self, response: Response) -> None:
        """Set CSRF token in response as secure, httpOnly cookie."""
        token = self._generate_token()
        response.set_cookie(
            key=self.COOKIE_NAME,
            value=token,
            max_age=3600,  # 1 hour
            secure=True,  # HTTPS only
            httponly=True,  # No JavaScript access
            samesite="Strict",  # Prevent cross-site requests
            path="/",
        )
        # Also send token in response header for JavaScript to read (for AJAX)
        response.headers[self.HEADER_NAME] = token


# ── Emit route tags ──────────────────────────────────────────────────────────
# Maps URL path prefixes to (channel_tag, value_weight, cost_weight).
# Requests arriving at these routes are gated by the emit value function.
# Routes not in this map are always admitted.
_ROUTE_EMIT_MAP: dict[str, tuple[str, float, float]] = {
    "/api/lead":             ("P", 1.0, 0.1),   # webhook lead ingest → Pipeline
    "/api/control/trigger":  ("X", 1.0, 0.2),   # admin overrides → Agent
    "/api/economy":          ("F", 1.0, 0.05),  # economy actions → Finance
    "/api/billing/invoices": ("F", 1.0, 0.05),  # invoice actions → Finance
    # Direct @app routes (no /api prefix after Vercel strip)
    "/lead":                 ("P", 1.0, 0.1),
    "/control/trigger":      ("X", 1.0, 0.2),
    "/state":                ("F", 1.0, 0.1),
    "/ingest/tasks":         ("J", 1.0, 0.1),
}


class EmitGatewayMiddleware(BaseHTTPMiddleware):
    """API gateway emit gate — routes tagged in _ROUTE_EMIT_MAP must pass value check.

    Non-GET, non-OPTIONS requests on tagged routes are evaluated:
        V = value_weight − cost_weight
    If V ≤ 0, the request is silenced with 204 No Content.
    All other routes pass through unconditionally.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        for prefix, (channel, value_w, cost_w) in _ROUTE_EMIT_MAP.items():
            if path.startswith(prefix):
                from app.core.emit import emit
                from app.core.emit import Channel
                ch = Channel(channel)
                if not emit(ch, values=[value_w], cost=cost_w):
                    from starlette.responses import Response as StarResponse
                    return StarResponse(status_code=204)
                break

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if current_time - t < 60
        ]

        if len(self.requests[client_ip]) >= self.requests_per_minute:
            from starlette.responses import PlainTextResponse
            return PlainTextResponse("Rate limit exceeded", status_code=429)

        self.requests[client_ip].append(current_time)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_ip])
        )

        return response  # type: ignore[no-any-return]


class AuthEndpointRateLimitMiddleware(BaseHTTPMiddleware):
    """Stricter rate limiting for /api/auth/* endpoints (5 req/min per IP)."""
    def __init__(self, app: Any):
        super().__init__(app)
        self.requests: dict[str, list[float]] = {}
        self.limit_per_minute = 5

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        # Only apply stricter limit to auth endpoints
        if not path.startswith("/api/auth/") and not path.startswith("/auth/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if current_time - t < 60
        ]

        if len(self.requests[client_ip]) >= self.limit_per_minute:
            from starlette.responses import PlainTextResponse
            return PlainTextResponse("Auth rate limit exceeded", status_code=429)

        self.requests[client_ip].append(current_time)

        response = await call_next(request)
        response.headers["X-RateLimit-Auth-Limit"] = str(self.limit_per_minute)
        response.headers["X-RateLimit-Auth-Remaining"] = str(
            self.limit_per_minute - len(self.requests[client_ip])
        )

        return response  # type: ignore[no-any-return]


class AdminEndpointRateLimitMiddleware(BaseHTTPMiddleware):
    """Stricter rate limiting for /admin/* endpoints (10 req/min per IP)."""
    def __init__(self, app: Any):
        super().__init__(app)
        self.requests: dict[str, list[float]] = {}
        self.limit_per_minute = 10

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        # Only apply stricter limit to admin endpoints
        if not path.startswith("/admin/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if current_time - t < 60
        ]

        if len(self.requests[client_ip]) >= self.limit_per_minute:
            from starlette.responses import PlainTextResponse
            return PlainTextResponse("Admin rate limit exceeded", status_code=429)

        self.requests[client_ip].append(current_time)

        response = await call_next(request)
        response.headers["X-RateLimit-Admin-Limit"] = str(self.limit_per_minute)
        response.headers["X-RateLimit-Admin-Remaining"] = str(
            self.limit_per_minute - len(self.requests[client_ip])
        )

        return response  # type: ignore[no-any-return]


# ── Global emit boundary enforcement ────────────────────────────────────────

class EmitGateMiddleware(BaseHTTPMiddleware):
    """Global fail-safe: reads ``net`` from JSON response bodies.

    Any route that returns a JSON payload with ``net <= 0`` is silenced
    with 204 No Content. This closes the system at the boundary — no
    non-positive-value state can escape regardless of which layer produced it.

    Opt-out: responses without a ``net`` key pass through unchanged.
    Safe-paths (docs, health, static) are skipped to avoid overhead.
    """

    _SKIP_PREFIXES = ("/docs", "/redoc", "/openapi", "/health", "/public", "/ws")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Skip non-JSON and safe infrastructure paths
        ct = response.headers.get("content-type", "")
        if "application/json" not in ct:
            return response  # type: ignore[no-any-return]

        path = request.url.path
        for prefix in self._SKIP_PREFIXES:
            if path.startswith(prefix):
                return response  # type: ignore[no-any-return]

        try:
            # Buffer and inspect body
            body_bytes = b""
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()

            if body_bytes:
                data = json.loads(body_bytes)
                if isinstance(data, dict) and "net" in data:
                    if data["net"] <= 0:
                        return Response(status_code=204)

            # Rebuild response with buffered body
            from starlette.responses import Response as StarResponse
            return StarResponse(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=ct,
            )
        except Exception:  # nosec B110 — middleware must never crash the request pipeline
            pass

        return response  # type: ignore[no-any-return]


def apply_emit_gate(app: Any) -> None:
    """Register EmitGateMiddleware on a FastAPI/Starlette app."""
    app.add_middleware(EmitGateMiddleware)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # PHASE 1: CRITICAL SECURITY HARDENING
        # Eliminate ALL inline execution vectors and restrict external resources

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # ZERO INLINE EXECUTION — No unsafe-inline, no unsafe-eval anywhere
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "                    # Deny everything by default
            "script-src 'self'; "                      # Only self-hosted scripts, NO inline
            "style-src 'self'; "                       # Only self-hosted stylesheets, NO inline
            "img-src 'self' data:; "                   # Self + data URIs for embedded images
            "font-src 'self' data:; "                  # Self + data URIs for embedded fonts
            "connect-src 'self'; "                     # API calls to self only (no wildcards)
            "object-src 'none'; "                      # Disable plugins
            "frame-ancestors 'none'; "                 # Clickjacking protection
            "base-uri 'self'; "                        # Restrict base URL
            "form-action 'self'"                       # Restrict form submission
        )

        response.headers["Referrer-Policy"] = "no-referrer"  # Strictest: no referrer leaked
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        return response  # type: ignore[no-any-return]
