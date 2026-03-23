"""Unit tests for governance domain services."""
import pytest
from app.domains.governance.services import GovernanceServices


@pytest.fixture
def gov():
    return GovernanceServices()


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
    assert status["ok"] is True


def test_get_reputation(gov):
    rep = gov.get_reputation("agent-1")
    assert "score" in rep
    assert rep["agent_id"] == "agent-1"
