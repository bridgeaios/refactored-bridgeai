"""
Optional uvicorn entry when the working directory is ``backend/``::

    uvicorn main:app --host 0.0.0.0 --port 8000

Dockerfile uses ``app.main:app`` directly; this module re-exports the same ``app``.

API surface (also documented in SPEC.md) — routes are registered on ``app`` from ``app.main``:

- **GET /api/health** — JSON health; implementation: ``app.domains.infra.router`` (``HealthResponse``).
- **POST /api/telemetry** — body JSON; for monetization / SVG build hooks use
  ``{"event": "svg_build_completed", "merkle_root": "...", "files": N, ...}``
  (``event`` or ``type`` accepted). Implementation: ``post_api_telemetry`` in infra router.
- **GET /api/telemetry/svg-build** — recent buffered SVG build events (``get_svg_build_telemetry_recent``).
- **bridgeos.tvm** — ``/api/tvm`` Topic Vector Matrix (manifest ``docs/manifests/bridgeos.tvm.yaml``).

Do not duplicate route decorators here; edit ``app/domains/infra/router.py`` for behavior changes.
"""

from app.main import app

__all__ = ["app"]
