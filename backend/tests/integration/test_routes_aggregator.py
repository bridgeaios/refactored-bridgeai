"""
Verify the routes aggregator correctly mounts all domain routers.
Uses the real app instance so any missing include_router() call is caught.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

EXPECTED_PREFIXES = [
    "/api/treasury/status",       # economy
    "/api/marketplace/open",      # economy
    "/api/ubi/status",            # economy
    "/api/health",                # infra
    "/api/auth/login",            # infra
    "/api/twin/profile",          # twins
    "/api/competition/status",    # twins
    "/api/governance/proposals",  # governance
    "/api/sdg/status",            # governance
    "/api/network/status",        # network
    "/api/swarm/health",          # network
    "/api/projects",              # network
]


def _make_mock_memory():
    m = MagicMock()
    m.get = AsyncMock(return_value=None)
    m.set = AsyncMock(return_value=True)
    m.append = AsyncMock(return_value=True)
    m.get_recent = AsyncMock(return_value=[])
    _engine = MagicMock()
    _engine.claim_idempotency = AsyncMock(return_value=True)
    m._engine = _engine
    return m


@pytest.mark.asyncio
async def test_all_domain_routers_mounted():
    """All expected domain router paths return something other than 404."""
    from app.core.deps import get_memory
    from app.domains.infra.deps import require_jwt

    mock_mem = _make_mock_memory()
    app.dependency_overrides[get_memory] = lambda: mock_mem
    app.dependency_overrides[require_jwt] = lambda: {"sub": "test", "authority": "test"}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for path in EXPECTED_PREFIXES:
                resp = await client.get(path)
                assert resp.status_code != 404, f"Domain router not mounted — {path} returned 404"
    finally:
        app.dependency_overrides.pop(get_memory, None)
        app.dependency_overrides.pop(require_jwt, None)
