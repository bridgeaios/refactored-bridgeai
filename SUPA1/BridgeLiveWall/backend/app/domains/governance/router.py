# ruff: noqa: B008
"""Governance domain: mission board, skills, SDG, proposal stubs."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.domains.governance.deps import get_governance
from app.domains.governance.models import GovernanceProposalRequest, GovernanceVoteRequest
from app.domains.governance.services import GovernanceServices
from app.runtime import mission_service, sdg_service

router = APIRouter(tags=["governance"])
# mission_service used by /skills; board uses GovernanceServices for parity with tests.


class SkillModel(BaseModel):
    name: str
    tags: list[str]
    description: str | None = None


@router.post("/skills")
async def add_skill(skill: SkillModel) -> dict[str, Any]:
    await mission_service.save_skill(skill.model_dump())
    return {"ok": True}


@router.get("/mission/board")
async def mission_board_route(svc: GovernanceServices = Depends(get_governance)) -> dict[str, Any]:
    return await svc.mission_board()


@router.get("/governance/proposals")
async def list_proposals(svc: GovernanceServices = Depends(get_governance)) -> dict[str, Any]:
    proposals = await svc.get_proposals()
    return {"ok": True, "proposals": proposals}


@router.post("/governance/propose")
async def submit_proposal(
    payload: GovernanceProposalRequest,
    svc: GovernanceServices = Depends(get_governance),
) -> dict[str, Any]:
    return await svc.submit_proposal(
        title=payload.title,
        description=payload.description,
        proposer_id=payload.proposer_id,
        payload=payload.payload,
    )


@router.post("/governance/vote")
async def vote(
    payload: GovernanceVoteRequest,
    svc: GovernanceServices = Depends(get_governance),
) -> dict[str, Any]:
    return await svc.vote(
        proposal_id=payload.proposal_id,
        voter_id=payload.voter_id,
        vote=payload.vote,
    )


@router.get("/reputation/{agent_id}")
async def get_reputation(
    agent_id: str,
    svc: GovernanceServices = Depends(get_governance),
) -> dict[str, Any]:
    return svc.get_reputation(agent_id)


@router.get("/sdg/status")
async def sdg_status(svc: GovernanceServices = Depends(get_governance)) -> dict[str, Any]:
    return await svc.sdg_status()


@router.get("/sdg/metrics")
async def sdg_metrics() -> dict[str, Any]:
    return sdg_service.get_metrics()


@router.get("/knowledge-graph/query")
async def kg_query(
    label: str = "",
    svc: GovernanceServices = Depends(get_governance),
) -> dict[str, Any]:
    return await svc.knowledge_graph_query(label=label)

