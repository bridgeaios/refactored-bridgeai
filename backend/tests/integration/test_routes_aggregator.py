"""
Verify the routes aggregator correctly mounts all domain routers.
Uses the real app instance so any missing include_router() call is caught.
"""
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


@pytest.mark.asyncio
async def test_all_domain_routers_mounted():
    """All expected domain router paths return something other than 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in EXPECTED_PREFIXES:
            resp = await client.get(path)
            assert resp.status_code != 404, f"Domain router not mounted — {path} returned 404"
