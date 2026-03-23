"""
Thin routes aggregator — all domain routers for /api prefix.
"""
from app.domains.economy.router import router as economy_router
from app.domains.governance.router import router as governance_router
from app.domains.infra.router import router as infra_router
from app.domains.network.router import router as network_router
from app.domains.twins.router import router as twins_router

all_routers = [
    economy_router,
    infra_router,
    twins_router,
    governance_router,
    network_router,
]
