"""Charts router — serves SVG analytics charts for the dashboard."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.domains.infra.deps import require_jwt

router = APIRouter(prefix="/charts", tags=["charts"])


def _svg_response(svg: str) -> Response:
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/pipeline")
async def pipeline_chart(_: dict = Depends(require_jwt)) -> Response:
    """Pipeline funnel SVG — reads live data from CRM service."""
    from app.domains.crm.deps import get_crm
    crm = get_crm()
    pipeline = await crm.pipeline()
    counts = {stage: len(leads) for stage, leads in pipeline.items()}

    from app.services.svg_generator import pipeline_funnel
    return _svg_response(pipeline_funnel(counts))


@router.get("/revenue")
async def revenue_chart(_: dict = Depends(require_jwt)) -> Response:
    """Monthly revenue bar chart SVG — reads from billing service."""
    from app.domains.billing.deps import get_billing
    billing = get_billing()
    invoices = await billing.list_invoices(status="paid", limit=500)

    # Aggregate by month
    monthly: dict[str, float] = {}
    for inv in invoices:
        paid_at = inv.get("paid_at") or inv.get("issued_at") or ""
        if len(paid_at) >= 7:
            key = paid_at[:7]  # YYYY-MM
            monthly[key] = monthly.get(key, 0) + float(inv.get("total", 0))

    data = [
        {"month": k[5:], "revenue": round(v, 2)}
        for k, v in sorted(monthly.items())
    ]

    from app.services.svg_generator import revenue_bar
    return _svg_response(revenue_bar(data))


@router.get("/lead-scores")
async def lead_score_chart(_: dict = Depends(require_jwt)) -> Response:
    """Lead score histogram SVG."""
    from app.domains.crm.deps import get_crm
    crm = get_crm()
    leads = await crm.list_leads(limit=500)
    scores = [float(lead.get("score", 0)) for lead in leads]

    from app.services.svg_generator import lead_score_histogram
    return _svg_response(lead_score_histogram(scores))


@router.get("/agent-activity")
async def agent_activity_chart(_: dict = Depends(require_jwt)) -> Response:
    """Agent task activity sparkline SVG — last 24 task completions bucketed by hour."""
    from app.core.deps import get_memory
    mem = get_memory()

    # Fetch task telemetry buckets from memory (populated by worker_loop)
    buckets: list[int] = await mem.get("telemetry:hourly:tasks") or [0] * 24
    labels: list[str] = await mem.get("telemetry:hourly:labels") or [str(i) for i in range(len(buckets))]

    from app.services.svg_generator import agent_activity_sparkline
    return _svg_response(agent_activity_sparkline(buckets, labels))
