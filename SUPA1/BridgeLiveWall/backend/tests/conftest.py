import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domains.economy.services import EconomyServices
from app.domains.governance.services import GovernanceServices
from app.domains.infra.services import InfraServices
from app.domains.network.services import NetworkServices
from app.domains.twins.services import TwinsServices


@pytest.fixture
def mock_memory():
    """Minimal MemoryStore mock — avoids real Redis in unit tests."""
    mem = MagicMock()
    mem.get = AsyncMock(return_value=None)
    mem.set = AsyncMock(return_value=True)
    mem.append = AsyncMock(return_value=True)
    mem.get_recent = AsyncMock(return_value=[])
    mem.delete = AsyncMock(return_value=True)
    return mem


@pytest.fixture
def mock_economy(mock_memory):
    svc = MagicMock(spec=EconomyServices)
    svc.collect = AsyncMock(return_value={"ok": True, "tx_id": "tx-test", "splits": {}})
    svc.treasury_status = AsyncMock(return_value={"total": 0.0, "buckets": {}})
    svc.treasury_ledger = AsyncMock(return_value=[])
    svc.ubi_can_claim = AsyncMock(return_value=True)
    svc.ubi_distribute = AsyncMock(return_value={"ok": True, "amount": 100})
    svc.ubi_status = AsyncMock(
        return_value={"can_claim": True, "amount": 100, "period_seconds": 86400}
    )
    svc.get_tasks = MagicMock(return_value=[])
    svc.post_task = MagicMock(return_value={"ok": True, "task_id": 1})
    svc.accept_task = MagicMock(return_value={"ok": True})
    svc.complete_task = MagicMock(return_value={"ok": True})
    svc.revenue_summary = AsyncMock(return_value={"total": 0.0})
    return svc


@pytest.fixture
def mock_infra(mock_memory):
    svc = MagicMock(spec=InfraServices)
    svc.verify_siwe = AsyncMock(return_value={"ok": True, "token": "test"})
    svc.mem_get = AsyncMock(return_value=None)
    svc.mem_set = AsyncMock(return_value=True)
    svc.google_sheets_available = MagicMock(return_value=False)
    svc.youtube_available = MagicMock(return_value=False)
    return svc


@pytest.fixture
def mock_twins():
    svc = MagicMock(spec=TwinsServices)
    svc.get_profile = MagicMock(return_value={"twin_id": "default", "status": "active"})
    svc.decide = AsyncMock(return_value={"ok": True, "decision": "proceed"})
    svc.shared_xml = AsyncMock(return_value="<xml/>")
    svc.emotion_status = AsyncMock(return_value={})
    svc.emotion_update = AsyncMock(return_value={"ok": True})
    svc.speak = AsyncMock(return_value={"ok": True})
    svc.competition_status = AsyncMock(return_value={"ok": True})
    svc.list_bossbots = MagicMock(return_value=[])
    return svc


@pytest.fixture
def mock_governance(mock_memory):
    svc = MagicMock(spec=GovernanceServices)
    svc.get_proposals = AsyncMock(return_value=[])
    svc.submit_proposal = AsyncMock(return_value={"ok": True})
    svc.vote = AsyncMock(return_value={"ok": True})
    svc.get_reputation = MagicMock(return_value={"agent_id": "a1", "score": 0.5})
    svc.sdg_status = AsyncMock(return_value={"ok": True})
    svc.knowledge_graph_query = AsyncMock(return_value={"ok": True, "nodes": []})
    svc.mission_board = AsyncMock(return_value={"ok": True})
    return svc


@pytest.fixture
def mock_network(mock_memory):
    svc = MagicMock(spec=NetworkServices)
    svc.network_status = AsyncMock(return_value={"ok": True})
    svc.swarm_health = AsyncMock(return_value={"ok": True, "nodes": []})
    svc.swarm_broadcast = AsyncMock(return_value={"ok": True})
    svc.list_projects = AsyncMock(return_value=[])
    svc.register_project = AsyncMock(return_value={"ok": True})
    return svc
