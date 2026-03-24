"""
Governance domain router.
Absorbs governance/*, knowledge-graph/*, reputation/*, mission/*, sdg/* from routes/api.py.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.domains.governance.deps import get_governance
from app.domains.governance.models import (
    GovernanceProposalRequest,
    GovernanceVoteRequest,
)
from app.domains.governance.services import GovernanceServices

router = APIRouter(tags=["governance"])

GovernanceDep = Annotated[GovernanceServices, Depends(get_governance)]


@router.get("/governance/proposals")
async def list_proposals(svc: GovernanceDep) -> dict[str, Any]:
    proposals = await svc.get_proposals()
    return {"ok": True, "proposals": proposals}


@router.post("/governance/propose")
async def submit_proposal(
    payload: GovernanceProposalRequest,
    svc: GovernanceDep,
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
    svc: GovernanceDep,
) -> dict[str, Any]:
    return await svc.vote(
        proposal_id=payload.proposal_id,
        voter_id=payload.voter_id,
        vote=payload.vote,
    )


@router.get("/reputation/{agent_id}")
async def get_reputation(
    agent_id: str,
    svc: GovernanceDep,
) -> dict[str, Any]:
    return svc.get_reputation(agent_id)


@router.get("/sdg/status")
async def sdg_status(svc: GovernanceDep) -> dict[str, Any]:
    return await svc.sdg_status()


@router.get("/knowledge-graph/query")
async def kg_query(
    svc: GovernanceDep,
    label: str = "",
) -> dict[str, Any]:
    return await svc.knowledge_graph_query(label=label)


@router.get("/mission/board")
async def mission_board(svc: GovernanceDep) -> dict[str, Any]:
    return await svc.mission_board()
