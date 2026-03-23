"""
Mission Economy Service - Token and Marketplace for Bridge Twin System.

Token: $BRDG (Bridge Token)
Streams:
- UBI Pool: 40% - Base income for all agents
- Treasury: 30% - Platform development
- Operations: 20% - Running costs
- Founder: 10% - Core team
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class MissionTier(str, Enum):
    """Mission tier pricing."""
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


MISSION_TIERS = {
    MissionTier.MICRO: {"price_usd": 10, "brdg_reward": 5},
    MissionTier.SMALL: {"price_usd": 50, "brdg_reward": 25},
    MissionTier.MEDIUM: {"price_usd": 200, "brdg_reward": 100},
    MissionTier.LARGE: {"price_usd": 1000, "brdg_reward": 500},
    MissionTier.ENTERPRISE: {"price_usd": 5000, "brdg_reward": 2500},
}

AGENT_COMMISSION = Decimal("0.70")
PLATFORM_FEE = Decimal("0.30")


class MissionStatus(str, Enum):
    """Mission execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Mission(BaseModel):
    """Mission definition."""
    id: str
    title: str
    description: str
    tier: MissionTier
    price_usd: float
    brdg_reward: float
    required_skills: list[str] = []
    status: MissionStatus = MissionStatus.PENDING
    created_at: datetime
    updated_at: datetime
    assignee_id: Optional[str] = None
    creator_id: str
    rating: Optional[float] = None


@dataclass
class TokenAllocation:
    """Token allocation for mission payment."""
    total_brdg: Decimal
    agent_commission: Decimal
    platform_fee: Decimal
    ubi_pool: Decimal
    treasury: Decimal
    operations: Decimal


class MissionEconomyService:
    """Manages mission marketplace and token economics."""

    def __init__(self):
        self._missions: dict[str, Mission] = {}
        self._agent_earnings: dict[str, Decimal] = {}
        self._ubi_distributed: Decimal = Decimal("0")
        self._treasury_balance: Decimal = Decimal("0")

    def create_mission(
        self,
        title: str,
        description: str,
        tier: MissionTier,
        creator_id: str,
        required_skills: list[str] = None,
    ) -> Mission:
        """Create a new mission."""
        config = MISSION_TIERS[tier]
        mission = Mission(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            tier=tier,
            price_usd=config["price_usd"],
            brdg_reward=config["brdg_reward"],
            required_skills=required_skills or [],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            creator_id=creator_id,
        )
        self._missions[mission.id] = mission
        return mission

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get mission by ID."""
        return self._missions.get(mission_id)

    def list_missions(
        self,
        status: Optional[MissionStatus] = None,
        tier: Optional[MissionTier] = None,
    ) -> list[Mission]:
        """List missions with optional filters."""
        missions = list(self._missions.values())
        if status:
            missions = [m for m in missions if m.status == status]
        if tier:
            missions = [m for m in missions if m.tier == tier]
        return sorted(missions, key=lambda m: m.created_at, reverse=True)

    def assign_mission(self, mission_id: str, agent_id: str) -> bool:
        """Assign mission to agent."""
        mission = self._missions.get(mission_id)
        if not mission or mission.status != MissionStatus.PENDING:
            return False
        mission.assignee_id = agent_id
        mission.status = MissionStatus.IN_PROGRESS
        mission.updated_at = datetime.utcnow()
        return True

    def complete_mission(
        self,
        mission_id: str,
        rating: float,
    ) -> Optional[TokenAllocation]:
        """Complete mission and calculate token allocation."""
        mission = self._missions.get(mission_id)
        if not mission or mission.status != MissionStatus.IN_PROGRESS:
            return None

        mission.status = MissionStatus.COMPLETED
        mission.rating = rating
        mission.updated_at = datetime.utcnow()

        total = Decimal(str(mission.brdg_reward))
        agent_commission = total * AGENT_COMMISSION
        platform_fee = total * PLATFORM_FEE
        ubi_pool = platform_fee * Decimal("0.4")
        treasury = platform_fee * Decimal("0.3")
        operations = platform_fee * Decimal("0.2")

        allocation = TokenAllocation(
            total_brdg=total,
            agent_commission=agent_commission,
            platform_fee=platform_fee,
            ubi_pool=ubi_pool,
            treasury=treasury,
            operations=operations,
        )

        if mission.assignee_id:
            self._agent_earnings[mission.assignee_id] = (
                self._agent_earnings.get(mission.assignee_id, Decimal("0")) + agent_commission
            )

        self._ubi_distributed += ubi_pool
        self._treasury_balance += treasury

        return allocation

    def get_agent_earnings(self, agent_id: str) -> Decimal:
        """Get agent's total earnings."""
        return self._agent_earnings.get(agent_id, Decimal("0"))

    def get_treasury_balance(self) -> Decimal:
        """Get treasury balance."""
        return self._treasury_balance

    def get_ubi_distributed(self) -> Decimal:
        """Get total UBI distributed."""
        return self._ubi_distributed

    def get_mission_stats(self) -> dict:
        """Get marketplace statistics."""
        completed = [m for m in self._missions.values() if m.status == MissionStatus.COMPLETED]
        total_value = sum(m.brdg_reward for m in completed)
        avg_rating = sum(m.rating for m in completed if m.rating) / len(completed) if completed else 0

        return {
            "total_missions": len(self._missions),
            "completed_missions": len(completed),
            "pending_missions": len([m for m in self._missions.values() if m.status == MissionStatus.PENDING]),
            "total_value_brdg": float(total_value),
            "average_rating": round(avg_rating, 2),
            "treasury_balance": float(self._treasury_balance),
            "ubi_distributed": float(self._ubi_distributed),
        }


_economy_service: Optional[MissionEconomyService] = None


def get_economy_service() -> MissionEconomyService:
    """Get global economy service."""
    global _economy_service
    if _economy_service is None:
        _economy_service = MissionEconomyService()
    return _economy_service
