"""
Thin routes aggregator — all domain routers in one list.

Usage in main.py:
    from app.routes import all_routers
    for r in all_routers:
        app.include_router(r, prefix="/api")
"""
from app.domains.billing.router import router as billing_router
from app.domains.crm.router import router as crm_router
from app.domains.economy.router import router as economy_router
from app.domains.governance.router import router as governance_router
from app.domains.infra.router import router as infra_router
from app.domains.network.router import router as network_router
from app.domains.outreach.router import router as outreach_router
from app.domains.twins.router import router as twins_router
from app.routes.charts import router as charts_router
from app.routes.controlplane import router as controlplane_router
from app.routes.observability import router as observability_router
from app.routes.webhooks import router as webhooks_router

all_routers = [
    crm_router,
    billing_router,
    outreach_router,
    economy_router,
    infra_router,
    twins_router,
    governance_router,
    network_router,
    charts_router,
    controlplane_router,
    observability_router,
    webhooks_router,
]
