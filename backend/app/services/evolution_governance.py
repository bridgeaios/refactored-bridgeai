"""
Evolution Governance Service - Mutation Framework, Quarantine, and Voting.

Manages agent evolution, mutation proposals, quarantine for dangerous agents,
and decentralized governance voting.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MutationType(str, Enum):
    """Types of agent mutations."""
    PARAMETER_TUNING = "parameter_tuning"
    ARCHITECTURE_CHANGE = "architecture_change"
    SKILL_ACQUISITION = "skill_acquisition"
    BEHAVIOR_ADAPTATION = "behavior_adaptation"
    EMERGENT_CAPABILITY = "emergent_capability"


class MutationStatus(str, Enum):
    """Status of mutation proposal."""
    PROPOSED = "proposed"
    TESTING = "testing"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class AgentStatus(str, Enum):
    """Agent operational status."""
    ACTIVE = "active"
    EVOLVING = "evolving"
    QUARANTINED = "quarantined"
    RETIRED = "retired"


class VoteType(str, Enum):
    """Type of governance vote."""
    MUTATION_APPROVAL = "mutation_approval"
    QUARANTINE_RELEASE = "quarantine_release"
    PARAMETER_CHANGE = "parameter_change"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


class VoteOption(str, Enum):
    """Voting options."""
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


@dataclass
class MutationProposal:
    """Mutation proposal for agent evolution."""
    id: str
    agent_id: str
    mutation_type: MutationType
    description: str
    changes: dict
    risk_score: float
    expected_benefit: float
    status: MutationStatus = MutationStatus.PROPOSED
    proposer_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    test_results: dict | None = None
    approval_votes: float = 0.0
    rejection_votes: float = 0.0


@dataclass
class AgentSnapshot:
    """Agent state snapshot for rollback."""
    agent_id: str
    state: dict
    parameters: dict
    timestamp: datetime


@dataclass
class QuarantineRecord:
    """Quarantine record for dangerous agents."""
    agent_id: str
    reason: str
    severity: str
    violations: list[str]
    quarantined_at: datetime
    released_at: datetime | None = None
    release_conditions: list[str] = field(default_factory=list)


@dataclass
class Vote:
    """Governance vote."""
    id: str
    vote_type: VoteType
    target_id: str
    voter_id: str
    option: VoteOption
    weight: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""


class GovernanceConfig:
    """Governance configuration."""

    MUTATION_RISK_THRESHOLD = 0.7
    QUARANTINE_SEVERITY_THRESHOLD = 0.8
    VOTE_QUORUM = 0.5
    APPROVAL_THRESHOLD = 0.66
    ROLLBACK_WINDOW_HOURS = 24


class EvolutionGovernance:
    """Manages agent evolution and governance."""

    def __init__(self):
        self._mutations: dict[str, MutationProposal] = {}
        self._agent_snapshots: dict[str, list[AgentSnapshot]] = {}
        self._quarantine: dict[str, QuarantineRecord] = {}
        self._votes: dict[str, Vote] = {}
        self._agent_status: dict[str, AgentStatus] = {}
        self._pending_votes: dict[str, list[str]] = {}

    def create_mutation_proposal(
        self,
        agent_id: str,
        mutation_type: MutationType,
        description: str,
        changes: dict,
        proposer_id: str,
    ) -> MutationProposal:
        """Create mutation proposal."""
        risk_score = self._calculate_risk_score(changes)
        expected_benefit = self._calculate_expected_benefit(changes)

        mutation = MutationProposal(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            mutation_type=mutation_type,
            description=description,
            changes=changes,
            risk_score=risk_score,
            expected_benefit=expected_benefit,
            proposer_id=proposer_id,
        )
        self._mutations[mutation.id] = mutation
        self._save_snapshot(agent_id)
        return mutation

    def _calculate_risk_score(self, changes: dict) -> float:
        """Calculate risk score for changes."""
        risk_factors = {
            "architecture_change": 0.4,
            "parameter_tuning": 0.1,
            "skill_acquisition": 0.2,
            "behavior_adaptation": 0.3,
            "emergent_capability": 0.5,
        }
        base_risk = risk_factors.get(changes.get("type", "parameter_tuning"), 0.2)
        complexity_factor = len(changes.get("changes", {})) * 0.05
        return min(1.0, base_risk + complexity_factor)

    def _calculate_expected_benefit(self, changes: dict) -> float:
        """Calculate expected benefit from changes."""
        return float(changes.get("expected_improvement", 0.5))

    def _save_snapshot(self, agent_id: str) -> None:
        """Save agent snapshot for rollback."""
        if agent_id not in self._agent_snapshots:
            self._agent_snapshots[agent_id] = []
        snapshot = AgentSnapshot(
            agent_id=agent_id,
            state={"status": "snapshot"},
            parameters={"version": len(self._agent_snapshots[agent_id]) + 1},
            timestamp=datetime.now(timezone.utc),
        )
        self._agent_snapshots[agent_id].append(snapshot)

    def approve_mutation(self, mutation_id: str) -> bool:
        """Approve mutation after testing."""
        mutation = self._mutations.get(mutation_id)
        if not mutation or mutation.status != MutationStatus.TESTING:
            return False
        if mutation.risk_score > GovernanceConfig.MUTATION_RISK_THRESHOLD:
            return False

        mutation.status = MutationStatus.APPROVED
        self._agent_status[mutation.agent_id] = AgentStatus.EVOLVING
        return True

    def reject_mutation(self, mutation_id: str) -> bool:
        """Reject mutation proposal."""
        mutation = self._mutations.get(mutation_id)
        if not mutation:
            return False
        mutation.status = MutationStatus.REJECTED
        return True

    def rollback_mutation(self, agent_id: str) -> bool:
        """Rollback agent to previous snapshot."""
        snapshots = self._agent_snapshots.get(agent_id, [])
        if not snapshots:
            return False

        mutation = next(
            (m for m in self._mutations.values() if m.agent_id == agent_id),
            None,
        )
        if mutation:
            mutation.status = MutationStatus.ROLLED_BACK
        self._agent_status[agent_id] = AgentStatus.ACTIVE
        return True

    def quarantine_agent(
        self,
        agent_id: str,
        reason: str,
        severity: float,
        violations: list[str],
    ) -> QuarantineRecord:
        """Quarantine dangerous agent."""
        record = QuarantineRecord(
            agent_id=agent_id,
            reason=reason,
            severity="high" if severity > GovernanceConfig.QUARANTINE_SEVERITY_THRESHOLD else "medium",
            violations=violations,
            quarantined_at=datetime.now(timezone.utc),
            release_conditions=[
                "Pass safety review",
                "Complete rehabilitation period",
                "Get approval vote",
            ],
        )
        self._quarantine[agent_id] = record
        self._agent_status[agent_id] = AgentStatus.QUARANTINED
        return record

    def get_quarantine_status(self, agent_id: str) -> QuarantineRecord | None:
        """Get quarantine status."""
        return self._quarantine.get(agent_id)

    def release_from_quarantine(self, agent_id: str) -> bool:
        """Release agent from quarantine after approval."""
        record = self._quarantine.get(agent_id)
        if not record or record.released_at:
            return False
        record.released_at = datetime.now(timezone.utc)
        self._agent_status[agent_id] = AgentStatus.ACTIVE
        return True

    def submit_vote(
        self,
        vote_type: VoteType,
        target_id: str,
        voter_id: str,
        option: VoteOption,
        weight: float = 1.0,
        reason: str = "",
    ) -> Vote:
        """Submit governance vote."""
        vote = Vote(
            id=str(uuid.uuid4()),
            vote_type=vote_type,
            target_id=target_id,
            voter_id=voter_id,
            option=option,
            weight=weight,
            reason=reason,
        )
        self._votes[vote.id] = vote

        if target_id not in self._pending_votes:
            self._pending_votes[target_id] = []
        self._pending_votes[target_id].append(vote.id)

        if vote_type == VoteType.MUTATION_APPROVAL:
            mutation = self._mutations.get(target_id)
            if mutation:
                if option == VoteOption.YES:
                    mutation.approval_votes += weight
                elif option == VoteOption.NO:
                    mutation.rejection_votes += weight
                self._check_mutation_votes(mutation)

        return vote

    def _check_mutation_votes(self, mutation: MutationProposal) -> None:
        """Check if mutation has enough votes for approval."""
        total = mutation.approval_votes + mutation.rejection_votes
        if total >= GovernanceConfig.VOTE_QUORUM:
            approval_rate = mutation.approval_votes / total
            if approval_rate >= GovernanceConfig.APPROVAL_THRESHOLD:
                mutation.status = MutationStatus.TESTING
            elif approval_rate < (1 - GovernanceConfig.APPROVAL_THRESHOLD):
                mutation.status = MutationStatus.REJECTED

    def get_vote_results(self, target_id: str) -> dict:
        """Get voting results for target."""
        vote_ids = self._pending_votes.get(target_id, [])
        votes = [self._votes[vid] for vid in vote_ids]

        yes_weight = sum(v.weight for v in votes if v.option == VoteOption.YES)
        no_weight = sum(v.weight for v in votes if v.option == VoteOption.NO)
        abstain_weight = sum(v.weight for v in votes if v.option == VoteOption.ABSTAIN)
        total_weight = yes_weight + no_weight + abstain_weight

        return {
            "yes": yes_weight,
            "no": no_weight,
            "abstain": abstain_weight,
            "total": total_weight,
            "approval_rate": yes_weight / total_weight if total_weight > 0 else 0,
            "quorum_met": total_weight >= GovernanceConfig.VOTE_QUORUM,
        }

    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get agent operational status."""
        return self._agent_status.get(agent_id, AgentStatus.ACTIVE)

    def get_mutation(self, mutation_id: str) -> MutationProposal | None:
        """Get mutation by ID."""
        return self._mutations.get(mutation_id)

    def list_mutations(self, status: MutationStatus | None = None) -> list[MutationProposal]:
        """List mutations with optional filter."""
        mutations = list(self._mutations.values())
        if status:
            mutations = [m for m in mutations if m.status == status]
        return sorted(mutations, key=lambda m: m.created_at, reverse=True)

    def get_governance_stats(self) -> dict:
        """Get governance statistics."""
        return {
            "total_mutations": len(self._mutations),
            "approved_mutations": len([m for m in self._mutations.values() if m.status == MutationStatus.APPROVED]),
            "pending_mutations": len([m for m in self._mutations.values() if m.status == MutationStatus.PROPOSED]),
            "quarantined_agents": len([r for r in self._quarantine.values() if not r.released_at]),
            "active_agents": len([s for s in self._agent_status.values() if s == AgentStatus.ACTIVE]),
        }


_governance_service: EvolutionGovernance | None = None


def get_governance_service() -> EvolutionGovernance:
    """Get global governance service."""
    global _governance_service
    if _governance_service is None:
        _governance_service = EvolutionGovernance()
    return _governance_service
