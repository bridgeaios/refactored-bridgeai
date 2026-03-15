"""
Runtime singletons — shared service instances across API routes and background tasks.

This fixes a subtle but critical coherence issue:
- if routes and lifespan create different MemoryStore / service instances,
  you get "it runs but nothing updates" (split-brain state).
"""

from app.services.memory_store import MemoryStore
from app.services.mission import MissionService
from app.services.emotion import EmotionService
from app.services.governance import GovernanceService
from app.services.learning import LearningService
from app.services.esim import EsimService
from app.services.ubi import UbiService
from app.services.marketplace import MarketplaceService
from app.services.sdg import SdgService
from app.services.revenue import RevenueService
from app.services.bossbots import BossBotsService
from app.services.twins_competition import TwinsCompetitionService
from app.services.voice_broker import VoiceBroker
from app.services.speech_reasoning import SpeechReasoningService
from app.services.cognitive_twin import CognitiveTwinService
from app.services.speech_embodiment import SpeechEmbodimentService
from app.services.system_comprehension import SystemComprehensionService
from app.services.replication import ReplicationEngine


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

# AI/speech systems.
cognitive_twin = CognitiveTwinService()
voice_broker = VoiceBroker()
speech_reasoning = SpeechReasoningService()
speech_embodiment = SpeechEmbodimentService()
system_comprehension = SystemComprehensionService()

