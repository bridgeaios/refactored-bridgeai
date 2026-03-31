import json
import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

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

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' http://localhost:* https://*; "
            "font-src 'self' data:;"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response  # type: ignore[no-any-return]
