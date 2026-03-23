# BridgeLiveWall Codebase Refactor — Design Spec

**Date:** 2026-03-23
**Branch:** `refactor/domain-modular` (parallel to `win-for-twin`)
**Approach:** Domain-Driven Modular Monolith + Unified React SPA

---

## Problem Statement

The BridgeLiveWall codebase has grown organically and suffers from five compounding issues:

1. **`api.py` is a 68.5K monolith** — 50+ endpoints in one file, nearly impossible to navigate or change safely
2. **43 loosely-coupled service files with silent failures** — widespread `except Exception: pass` means bugs hide and nothing fails loudly
3. **Inconsistent patterns** — mix of class-based and function-based services, async and sync, in-memory and Redis state, no enforced conventions
4. **Frontend fragmentation** — 39 loose vanilla JS modules + 20+ HTML pages + a separate React DeFi app with no unified architecture
5. **Duplicate concerns** — `treasury.py` exists as both route and service, `marketplace.py` appears twice, two competing entry points

---

## Goals

- Consistent patterns everywhere (async-first I/O, DI, typed contracts)
- No silent failures — every error surface is explicit
- Testable by default — DI makes mocking trivial
- Single unified frontend — React SPA covering all pages
- All existing API endpoints preserved at same paths (no breaking changes)
- CI green throughout

---

## Non-Goals

- Microservices split (over-engineered for current scale)
- Rewriting the Babylon.js 3D renderer (wrap, don't rewrite)
- Changing the core business logic (economic model, SIWE auth, twin behavior)

---

## Approach: Domain-Driven Modular Monolith

### Migration Strategy

Parallel rewrite on branch `refactor/domain-modular`. Old code stays untouched on `win-for-twin`. Cut over when:

1. All existing API endpoints reachable at same paths
2. CI green (ruff, mypy, pytest, frontend build)
3. Playwright E2E passes for 5 critical flows
4. Docker Compose stack boots clean

### Migration Order

Work in this sequence to minimize cross-domain conflicts and keep CI green at each step:

1. **Scaffold `core/`** — errors, types, base DI factories. No business logic; all domains depend on this.
2. **Migrate `economy` domain end-to-end** — it has the most existing test coverage and touches treasury, marketplace, UBI, and payment_rails. Use it as the template for all other domains.
3. **Migrate `infra` domain** — memory_store, telemetry, siwe_auth. Other domains depend on these services; having them in the new structure unblocks parallel work.
4. **Migrate remaining domains in parallel** — `twins`, `governance`, `network` can proceed concurrently once `core/` and `infra` are stable.
5. **Freeze vanilla JS frontend** — once all backend domains are migrated and CI is green.
6. **Build React SPA** — scaffold `AppShell`, then migrate pages domain by domain following the same economy-first ordering.

---

## Backend Architecture

### Current State of Routes (Partial Split Already Exists)

The backend routes layer has already been partially extracted. The following files exist and must be accounted for in the domain mapping:

| Existing File | Lines | Disposition |
| --- | --- | --- |
| `routes/api.py` | 68.5K | Split — each endpoint group moves into its domain router |
| `routes/auth.py` | 1.9K | Folds into `domains/infra/router.py` |
| `routes/treasury.py` | 11.3K | Folds into `domains/economy/router.py` |
| `routes/projects.py` | 2.8K | Folds into `domains/network/router.py` |
| `routes/cli.py` | 5.3K | Folds into `domains/infra/router.py` |

None of these files are discarded — their logic is absorbed into domain routers.

The `routes/` directory becomes a thin aggregator. After migration it contains a single `__init__.py` that includes all domain routers into the main app:

```python
# routes/__init__.py
from app.domains.economy.router import router as economy_router
from app.domains.twins.router import router as twins_router
from app.domains.governance.router import router as governance_router
from app.domains.network.router import router as network_router
from app.domains.infra.router import router as infra_router

all_routers = [economy_router, twins_router, governance_router, network_router, infra_router]
```

All individual route files under `routes/` are deleted after their logic is absorbed.

### Domain Package Structure

```text
backend/app/
├── domains/
│   ├── economy/          # treasury, revenue, ubi, marketplace, payment_rails, demand_engine, econ_control
│   ├── twins/            # cognitive_twin, twins_competition, speech_*, emotion, system_comprehension, evolution_governance
│   ├── governance/       # governance, knowledge_graph, reputation, mission_economy
│   ├── network/          # replication, swarm_message_bus, swarm_health, projects, automation
│   └── infra/            # memory_store, telemetry, siwe_auth, google_sheets, neo4j_connection
├── core/
│   ├── errors.py         # domain exception hierarchy
│   ├── deps.py           # shared DI factories
│   └── types.py          # shared Pydantic base models
├── routes/               # thin aggregator — imports domain routers
└── main.py               # app factory only — wires DI, includes routers, lifespan
```

Each domain package is self-contained:

```text
economy/
├── __init__.py
├── router.py       # FastAPI router (replaces slice of api.py)
├── services.py     # business logic
├── models.py       # Pydantic schemas for this domain
└── deps.py         # FastAPI Depends() factories
```

### Pattern: Dependency Injection

Services are no longer module-level singletons accessed globally. Each route declares its dependencies explicitly:

```python
@router.post("/treasury/collect")
async def collect(
    payload: CollectRequest,
    svc: TreasuryService = Depends(get_treasury_service)
):
    return await svc.collect(payload)
```

`get_treasury_service` in `economy/deps.py` returns a cached instance. Fully testable — swap real service for mock in tests via `app.dependency_overrides`.

### Pattern: Structured Error Handling

Replace `except Exception: pass` with a domain exception hierarchy:

```python
# core/errors.py
class BridgeError(Exception): ...
class NotFoundError(BridgeError): ...
class ValidationError(BridgeError): ...
class EconomicGateError(BridgeError): ...   # execution_gate rejections
class AuthError(BridgeError): ...
class NetworkError(BridgeError): ...
```

Global FastAPI exception handler converts all `BridgeError` subclasses to consistent JSON:

```json
{ "ok": false, "code": "ECONOMIC_GATE_ERROR", "message": "Task value ≤ cost, rejected" }
```

### Pattern: Async-First

- All services that touch I/O (Redis, Neo4j, HTTP, filesystem) are `async`
- In-memory-only services may stay sync
- No mixing within a single service class

---

## Frontend Architecture

### Unified React SPA

#### Current State of `bridge_defi/frontend`

`bridge_defi/frontend` is currently a **DeFi-specific app** — it contains `Dashboard.tsx`, `Lending.tsx`, `Staking.tsx`, `Dex.tsx`, `Treasury.tsx`, and `Terminal.tsx`. It has no AppShell, no router, and no page structure beyond the DeFi use case.

The refactor **substantially restructures** this directory rather than building on an existing scaffold. The DeFi components (`Lending`, `Staking`, `Dex`) are preserved as the `economy` domain. The rest of the domain structure is new. A new `frontend-v2/` directory is **not** created — the refactor happens in place within `bridge_defi/frontend` to keep the git history and avoid renaming the Docker build target.

All frontend functionality consolidates here. The vanilla JS app (`frontend/`) is frozen — no new development.

```text
bridge_defi/frontend/src/
├── domains/
│   ├── economy/          # Treasury, Revenue, UBI, Marketplace, CFO (includes existing Lending/Staking/Dex)
│   ├── twins/            # DigitalTwin, Agents, Competition, Speech, Emotion
│   ├── governance/       # Governance, KnowledgeGraph, Reputation, Missions
│   ├── network/          # NetworkDashboard, Swarm, BAN, Status
│   └── infra/            # Settings, Docs, Sitemap, Auth/Gateway
├── core/
│   ├── api/              # typed API client (generated from OpenAPI specs)
│   ├── hooks/            # useWallet, useWebSocket, useApi
│   ├── components/       # shared UI primitives
│   └── theme/            # design tokens from bridge-theme.css
├── layouts/
│   ├── AppShell.tsx      # nav + sidebar + topbar
│   └── GatewayShell.tsx  # SIWE auth wrapper
├── pages/                # one file per route
└── App.tsx               # React Router — all routes
```

### Page → Route Mapping

| Current HTML | React Route |
| --- | --- |
| `index.html` | `/` |
| `executive-dashboard.html` | `/dashboard` |
| `gateway/index.html` | `/gateway` |
| `agents.html` | `/agents` |
| `cfo.html` | `/cfo` |
| `network-dashboard.html` | `/network` |
| `50-applications.html` | `/apps` |
| `join.html` | `/join` |
| `settings.html` | `/settings` |
| `docs.html` | `/docs` |
| `ban-live-wall.html` | `/ban` |
| `control-plane.html` | `/control` |
| `status.html` | `/status` |
| `landing.html` | `/landing` |

### Babylon.js Strategy

`babylonRenderer.js` (61.2K) is wrapped rather than rewritten:

```tsx
// domains/twins/BabylonCanvas.tsx
const BabylonCanvas = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const engine = initBabylonEngine(canvasRef.current); // existing logic unchanged
    return () => engine.dispose();
  }, []);
  return <canvas ref={canvasRef} className="twin-canvas" />;
};
```

React manages layout, data, and nav. Babylon manages the canvas. No 3D code rewrite.

### Typed API Client

#### Prerequisite: Reconcile OpenAPI Specs

The repo contains multiple spec files (`openapi.internal.json`, `openapi.v2.public.json`, `openapi.runtime-expanded.json`, `openapi.runtime-supplement.json`) that have drifted from the live API (see `docs/API-DRIFT-REPORT.md`). Before generating the client:

1. Boot the backend and capture the live spec: `GET /openapi.json`
2. Reconcile against `openapi.v2.public.json` using the drift report as a guide
3. Establish `openapi.v2.public.json` as the single source of truth
4. Add a CI step: `diff <(curl localhost:8000/openapi.json) openapi.v2.public.json` to catch future drift

The cut-over checklist verifies against the **live `/openapi.json` endpoint**, not the static file.

Generated from the reconciled spec via `openapi-typescript`:

```typescript
// core/api/client.ts
export const api = {
  economy: {
    collectRevenue: (payload: CollectRequest) => post('/treasury/collect', payload),
    getTreasuryStatus: () => get<TreasuryStatus>('/treasury/status'),
    getMarketplace: () => get<Task[]>('/marketplace/open'),
  },
  twins: {
    decide: (payload: DecideRequest) => post('/twin/decide', payload),
    getProfile: () => get<TwinProfile>('/twin/profile'),
    getSharedXml: () => get<string>('/twin/shared-xml'),
  },
  // ... one namespace per domain
};
```

Frontend/backend contract is enforced at build time. API drift is caught before it ships.

---

## Error Handling

### Backend

- Domain exception hierarchy (see above)
- Global FastAPI handler → consistent `{ ok, code, message }` JSON
- No bare `except:` anywhere — lint rule enforced via ruff

### Frontend

- React Error Boundaries per domain (economy, twins, governance, network)
- Shared `useApi` hook surfaces errors to UI rather than swallowing them
- All API calls return `{ ok: boolean, data?: T, error?: ApiError }`

---

## Testing Strategy

| Layer | Tool | Coverage Target |
| --- | --- | --- |
| Backend unit | `pytest` + `pytest-asyncio` | Each service in isolation via DI mocking |
| Backend integration | `pytest` + `httpx.AsyncClient` | Route → service → store round-trips |
| Frontend unit | `vitest` + `@testing-library/react` | Components, hooks, API client |
| Frontend E2E | `playwright` | 5 critical flows (see below) |

### 5 Critical E2E Flows (cut-over gate)

1. Gateway SIWE auth → redirect to dashboard
2. Marketplace: post task → accept → complete → revenue collected
3. Treasury collect → UBI bucket debited → UBI claim succeeds
4. Twin decide → response returned with deterministic output
5. Settings save → persisted → reflected on reload

Existing `conftest.py` fixtures are extended, not replaced.

---

## Cut-Over Checklist

- [ ] All API endpoints reachable at same paths (verified via live `GET /openapi.json` diff against reconciled `openapi.v2.public.json`)
- [ ] `ruff check` clean
- [ ] `mypy` clean
- [ ] `pytest` green with coverage ≥ existing baseline
- [ ] Frontend `vite build` clean
- [ ] Docker Compose stack boots (`docker compose up --build`)
- [ ] Playwright E2E: all 5 critical flows pass
- [ ] Merge `refactor/domain-modular` → `win-for-twin`

---

## File Disposition

| Current | Action |
| --- | --- |
| `backend/app/routes/api.py` (68.5K) | Split into 5 domain routers |
| `backend/app/services/*.py` (43 files) | Moved into domain packages, consolidated where duplicated |
| `backend/app/runtime.py` | Lifespan logic moves to `app/main.py` lifespan context manager; global singleton accessor pattern replaced by `Depends()` |
| `backend/main.py` (root) | Kept as a **separate standalone process** (merkle tree + telemetry); reassigned to port **8010** to avoid collision with the FastAPI app on 8000. Add as its own Docker Compose service on 8010. |
| `frontend/` (vanilla JS) | Frozen — no new development |
| `bridge_defi/frontend/` | Substantially restructured in-place to become the unified frontend |
| `backend/app/main.py` | Becomes pure app factory |
