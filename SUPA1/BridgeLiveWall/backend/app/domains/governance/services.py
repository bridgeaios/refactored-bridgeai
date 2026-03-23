"""Governance domain service facade."""
from __future__ import annotations

from typing import Any, Optional

from app.services.governance import GovernanceService
from app.services.memory_store import MemoryStore
from app.services.mission import MissionService
from app.services.sdg import SdgService


class GovernanceServices:
    def __init__(self, memory: Optional[MemoryStore] = None) -> None:
        self._memory = memory
        self._gov = GovernanceService(memory=memory)
        self._mission = MissionService(memory) if memory else None
        self._sdg = SdgService()

    async def get_proposals(self) -> list[dict]:
        return []

    async def submit_proposal(
        self,
        title: str,
        description: str,
        proposer_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        vote = {
            "type": "proposal",
            "title": title,
            "description": description,
            "proposer_id": proposer_id,
            **payload,
        }
        await self._gov.record_vote(vote)
        return {"ok": True, "proposal_id": "mock"}

    async def vote(self, proposal_id: str, voter_id: str, vote: str) -> dict[str, Any]:
        score = 1.0 if vote == "yes" else -1.0
        await self._gov.record_vote(
            {
                "proposal_id": proposal_id,
                "voter_id": voter_id,
                "vote": vote,
                "score": score,
            }
        )
        return {"ok": True}

    def get_reputation(self, agent_id: str) -> dict[str, Any]:
        return {"agent_id": agent_id, "score": 0.5}

    async def sdg_status(self) -> dict[str, Any]:
        return {"ok": True, "metrics": self._sdg.get_metrics()}

    async def knowledge_graph_query(
        self, label: str, properties: Optional[dict] = None
    ) -> dict[str, Any]:
        _ = label
        _ = properties
        return {"ok": True, "nodes": []}

    async def mission_board(self) -> dict[str, Any]:
        if self._mission and hasattr(self._mission, "get_counts"):
            return await self._mission.get_counts()
        return {"ok": True, "missions": {}}
