"""Unit tests for network domain services."""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_mem():
    m = MagicMock()
    m.get = AsyncMock(return_value=None)
    m.set = AsyncMock(return_value=True)
    m.get_recent = AsyncMock(return_value=[])
    return m


@pytest.fixture
def net(mock_mem):
    from app.domains.network.services import NetworkServices
    return NetworkServices(memory=mock_mem)


def test_network_services_instantiates(net):
    assert net is not None


@pytest.mark.asyncio
async def test_list_projects(net):
    projects = await net.list_projects()
    assert isinstance(projects, list)


@pytest.mark.asyncio
async def test_swarm_health(net):
    health = await net.swarm_health()
    assert isinstance(health, dict)
