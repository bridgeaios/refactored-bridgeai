"""
Runtime singletons — shared service instances across API routes and background tasks.

This fixes a subtle but critical coherence issue:
- if routes and lifespan create different MemoryStore / service instances,
  you get "it runs but nothing updates" (split-brain state).
"""

from app.services.bossbots import BossBotsService
from app.services.cognitive_twin import CognitiveTwinService
from app.services.emotion import EmotionService
from app.services.esim import EsimService
from app.services.governance import GovernanceService
from app.services.learning import LearningService
from app.services.marketplace import MarketplaceService
from app.services.memory_store import MemoryStore
from app.services.mission import MissionService
from app.services.projects import ProjectsService
from app.services.replication import ReplicationEngine
from app.services.revenue import RevenueService
from app.services.sdg import SdgService
from app.services.speech_embodiment import SpeechEmbodimentService
from app.services.speech_reasoning import SpeechReasoningService
from app.services.system_comprehension import SystemComprehensionService
from app.services.twins_competition import TwinsCompetitionService
from app.services.ubi import UbiService
from app.services.voice_broker import VoiceBroker
from app.services.demand_engine import DemandEngineService
from app.services.reputation import get_reputation_service
from app.services.swarm_health import SwarmHealthService
from app.services.econ_control import EconControlService

# Shared memory (Redis if available; file-backed fallback if not).
memory = MemoryStore()

# Shared services.
mission_service = MissionService(memory)
emotion_service = EmotionService()
gov_service = GovernanceService()
learning_service = LearningService()
esim_service = EsimService()
ubi_service = UbiService()
marketplace_service = MarketplaceService()
sdg_service = SdgService()
revenue_service = RevenueService()
bossbots_service = BossBotsService()
twins_competition = TwinsCompetitionService()
replication_engine = ReplicationEngine(memory, twins_competition, marketplace_service)

# Demand/reputation/health control loops.
demand_engine = DemandEngineService(marketplace_service)
reputation_service = get_reputation_service()

# Wire priority routing: marketplace uses twin reputation. Trust normalized [0.1, 1.0].
from app.services.priority_routing import normalize_trust
def _reputation_score(agent_id: str) -> float:
    r = reputation_service.get(agent_id)
    return normalize_trust(r.score())


marketplace_service.set_reputation_getter(_reputation_score)

# Project registry — single source of truth for all connected projects.
projects_service = ProjectsService(memory)

# Unified treasury — all projects route revenue through here.
from app.services.treasury import TreasuryService
treasury_service = TreasuryService(memory)

# Wire UBI to treasury so claims debit the UBI bucket.
ubi_service.set_treasury(treasury_service)

# AI/speech systems.
cognitive_twin = CognitiveTwinService()
voice_broker = VoiceBroker()
speech_reasoning = SpeechReasoningService()
speech_embodiment = SpeechEmbodimentService()
system_comprehension = SystemComprehensionService()

# Swarm health (uses physics telemetry if available at call sites).
swarm_health_service = SwarmHealthService()

# Economic control kernel — global weights, canonical w·P scoring, risk/capital gates.
econ_control = EconControlService(memory)
econ_control.set_reputation_getter(_reputation_score)

