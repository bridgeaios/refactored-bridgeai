"""
Integration tests for Bridge Twin System Services.

Tests for:
- Mission Economy Service
- Evolution Governance Service
- Knowledge Graph Service
- Swarm Message Bus Service
"""
import pytest
from decimal import Decimal
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.mission_economy import (
    MissionEconomyService,
    MissionTier,
    MissionStatus,
)
from app.services.evolution_governance import (
    EvolutionGovernance,
    MutationType,
    MutationStatus,
    AgentStatus,
    VoteType,
    VoteOption,
)
from app.services.knowledge_graph import (
    KnowledgeGraph,
    SkillLevel,
)
from app.services.swarm_message_bus import (
    SwarmMessageBus,
    AgentMessage,
    AgentEvent,
)


class TestMissionEconomyService:
    """Tests for Mission Economy Service."""

    def test_create_mission(self):
        """Test mission creation."""
        service = MissionEconomyService()
        mission = service.create_mission(
            title="Test Mission",
            description="A test mission",
            tier=MissionTier.SMALL,
            creator_id="creator-1",
            required_skills=["python", "fastapi"],
        )

        assert mission.title == "Test Mission"
        assert mission.tier == MissionTier.SMALL
        assert mission.price_usd == 50
        assert mission.brdg_reward == 25
        assert mission.status == MissionStatus.PENDING

    def test_assign_mission(self):
        """Test mission assignment."""
        service = MissionEconomyService()
        mission = service.create_mission(
            title="Test",
            description="Test",
            tier=MissionTier.MICRO,
            creator_id="creator-1",
        )

        result = service.assign_mission(mission.id, "agent-1")
        assert result is True
        assert mission.assignee_id == "agent-1"
        assert mission.status == MissionStatus.IN_PROGRESS

    def test_complete_mission_token_allocation(self):
        """Test mission completion with token allocation."""
        service = MissionEconomyService()
        mission = service.create_mission(
            title="Test",
            description="Test",
            tier=MissionTier.MEDIUM,
            creator_id="creator-1",
        )
        service.assign_mission(mission.id, "agent-1")

        allocation = service.complete_mission(mission.id, rating=5.0)

        assert allocation is not None
        assert allocation.total_brdg == Decimal("100")
        assert allocation.agent_commission == Decimal("70")
        assert allocation.platform_fee == Decimal("30")
        assert mission.status == MissionStatus.COMPLETED

    def test_mission_stats(self):
        """Test mission statistics."""
        service = MissionEconomyService()

        service.create_mission("M1", "D", MissionTier.MICRO, "c1")
        m2 = service.create_mission("M2", "D", MissionTier.SMALL, "c1")
        service.assign_mission(m2.id, "a1")
        service.complete_mission(m2.id, rating=4.5)

        stats = service.get_mission_stats()
        assert stats["total_missions"] == 2
        assert stats["completed_missions"] == 1


class TestEvolutionGovernance:
    """Tests for Evolution Governance Service."""

    def test_create_mutation_proposal(self):
        """Test mutation proposal creation."""
        gov = EvolutionGovernance()
        mutation = gov.create_mutation_proposal(
            agent_id="agent-1",
            mutation_type=MutationType.PARAMETER_TUNING,
            description="Tune learning rate",
            changes={"learning_rate": 0.01, "type": "parameter_tuning"},
            proposer_id="proposer-1",
        )

        assert mutation.agent_id == "agent-1"
        assert mutation.status == MutationStatus.PROPOSED
        assert mutation.risk_score < 0.5

    def test_quarantine_agent(self):
        """Test agent quarantine."""
        gov = EvolutionGovernance()
        record = gov.quarantine_agent(
            agent_id="agent-1",
            reason="Dangerous behavior",
            severity=0.9,
            violations=["harmful_output", "bypass_safety"],
        )

        assert record.agent_id == "agent-1"
        assert record.severity == "high"
        assert gov.get_agent_status("agent-1") == AgentStatus.QUARANTINED

    def test_vote_submission(self):
        """Test governance voting."""
        gov = EvolutionGovernance()
        mutation = gov.create_mutation_proposal(
            agent_id="agent-1",
            mutation_type=MutationType.SKILL_ACQUISITION,
            description="Learn new skill",
            changes={"skill": "data_analysis"},
            proposer_id="proposer-1",
        )

        vote = gov.submit_vote(
            vote_type=VoteType.MUTATION_APPROVAL,
            target_id=mutation.id,
            voter_id="voter-1",
            option=VoteOption.YES,
            weight=1.0,
        )

        assert vote.option == VoteOption.YES
        results = gov.get_vote_results(mutation.id)
        assert results["yes"] == 1.0


class TestKnowledgeGraph:
    """Tests for Knowledge Graph Service."""

    def test_register_agent(self):
        """Test agent registration."""
        kg = KnowledgeGraph()
        agent = kg.register_agent(
            agent_id="agent-1",
            name="Test Agent",
            role="analyst",
            expertise=["python", "data_analysis"],
            capabilities=["analysis", "reporting"],
        )

        assert agent.agent_id == "agent-1"
        assert "python" in agent.expertise

    def test_update_agent_skills(self):
        """Test skill update."""
        kg = KnowledgeGraph()
        kg.register_agent("agent-1", "Test", "dev", ["python"], [])

        result = kg.update_agent_skills(
            agent_id="agent-1",
            skills={"python": SkillLevel.EXPERT, "sql": SkillLevel.ADVANCED},
        )

        assert result is True
        agent = kg.get_agent("agent-1")
        assert agent.skills["python"] == SkillLevel.EXPERT

    def test_find_collaboration(self):
        """Test collaboration discovery."""
        kg = KnowledgeGraph()
        kg.register_agent("agent-1", "Alice", "dev", ["python", "api"], [], ["pair_programming"])
        kg.register_agent("agent-2", "Bob", "dev", ["python", "testing"], [], ["pair_programming"])

        opportunities = kg.discover_collaboration("agent-1")

        assert len(opportunities) > 0
        assert opportunities[0].agent_b_id == "agent-2"
        assert "python" in opportunities[0].shared_skills


class TestSwarmMessageBus:
    """Tests for Swarm Message Bus Service."""

    def test_message_bus_init(self):
        """Test message bus initialization."""
        bus = SwarmMessageBus(redis_url="redis://localhost:6379")
        assert bus.redis_url == "redis://localhost:6379"

    def test_agent_message_creation(self):
        """Test agent message creation."""
        msg = AgentMessage(
            sender_id="agent-1",
            recipient_id="agent-2",
            channel="test-channel",
            payload={"action": "test"},
            correlation_id="corr-1",
            timestamp=datetime.now(),
            event_type=AgentEvent.HEARTBEAT,
        )
        assert msg.sender_id == "agent-1"
        assert msg.event_type == AgentEvent.HEARTBEAT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
