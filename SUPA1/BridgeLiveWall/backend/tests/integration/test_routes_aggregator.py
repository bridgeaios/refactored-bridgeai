"""
Verify domain routers are mounted on the real app under /api.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_all_domain_routers_mounted():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/treasury/status")
        assert resp.status_code != 404, "Economy router not mounted"
        resp = await client.get("/api/health")
        assert resp.status_code != 404, "Infra router not mounted"
