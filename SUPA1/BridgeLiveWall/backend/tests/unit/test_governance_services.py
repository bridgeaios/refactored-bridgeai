import pytest

from app.domains.governance.services import GovernanceServices


@pytest.fixture
def gov(mock_memory):
    return GovernanceServices(memory=mock_memory)


def test_governance_services_instantiates(gov):
    assert gov is not None


@pytest.mark.asyncio
async def test_get_proposals(gov):
    proposals = await gov.get_proposals()
    assert isinstance(proposals, list)


@pytest.mark.asyncio
async def test_sdg_status(gov):
    status = await gov.sdg_status()
    assert isinstance(status, dict)
