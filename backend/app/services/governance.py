from app.services.memory_store import MemoryStore


class GovernanceService:
    def __init__(self, memory: MemoryStore | None = None):
        self.memory = memory or MemoryStore()

    async def compute_score(self):
        recent = await self.memory.get_recent("governance_votes", 100)
        if not recent:
            return 0.0
        # assume votes are dicts with 'score' in [-1,1]
        vals = [r.get('score',0) for r in recent if isinstance(r, dict)]
        if not vals:
            return 0.0
        return sum(vals)/len(vals)

    async def record_vote(self, vote: dict):
        await self.memory.append("governance_votes", vote)
        return True
