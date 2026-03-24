"""Governance domain service facade."""
from __future__ import annotations

import logging
from typing import Any

from app.services.governance import GovernanceService
from app.services.reputation import get_reputation_service
from app.services.sdg import SdgService

_log = logging.getLogger(__name__)


class GovernanceServices:
    """Aggregates all governance-domain services."""

    def __init__(self, memory: Any | None = None) -> None:
        self._gov = GovernanceService()
        self._rep = get_reputation_service()
        self._sdg = SdgService()
        self._kg = None
        self._mission = None
        try:
            from app.services.knowledge_graph import KnowledgeGraph
            self._kg = KnowledgeGraph()
        except Exception as exc:
            _log.warning("KnowledgeGraph unavailable: %s", exc)
        if memory:
            try:
                from app.services.mission import MissionService
                self._mission = MissionService(memory)
            except Exception as exc:
                _log.warning("MissionService unavailable: %s", exc)

    async def get_proposals(self) -> list[dict]:
        # GovernanceService has compute_score / record_vote — no proposal list yet
        return []

    async def submit_proposal(
        self, title: str, description: str, proposer_id: str, payload: dict
    ) -> dict[str, Any]:
        vote_entry = {"type": "proposal", "title": title, "proposer": proposer_id, **payload}
        await self._gov.record_vote(vote_entry)
        return {"ok": True, "proposal_id": f"prop-{title[:20]}"}

    async def vote(self, proposal_id: str, voter_id: str, vote: str) -> dict[str, Any]:
        await self._gov.record_vote({"proposal_id": proposal_id, "voter": voter_id, "vote": vote})
        return {"ok": True}

    def get_reputation(self, agent_id: str) -> dict[str, Any]:
        r = self._rep.get(agent_id)
        return {"agent_id": agent_id, "score": r.score() if hasattr(r, "score") else 0.5}

    async def sdg_status(self) -> dict[str, Any]:
        metrics = self._sdg.get_metrics()
        return {"ok": True, "sdgs": metrics}

    async def knowledge_graph_query(self, label: str, properties: dict | None = None) -> dict[str, Any]:
        if self._kg and hasattr(self._kg, "query"):
            return await self._kg.query(label=label, properties=properties or {})
        return {"ok": True, "nodes": []}

    async def mission_board(self) -> dict[str, Any]:
        if self._mission and hasattr(self._mission, "get_counts"):
            return await self._mission.get_counts()
        return {"ok": True, "missions": {}}
