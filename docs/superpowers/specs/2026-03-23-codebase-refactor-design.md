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

---

## Backend Architecture

### Domain Package Structure

```
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
```
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

All frontend functionality consolidates into `bridge_defi/frontend` (already React 18 + TypeScript). The vanilla JS app (`frontend/`) is frozen — no new development.

```
bridge_defi/frontend/src/
├── domains/
│   ├── economy/          # Treasury, Revenue, UBI, Marketplace, CFO
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
|---|---|
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

Generated from existing OpenAPI specs via `openapi-typescript`:

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
|---|---|---|
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

- [ ] All API endpoints reachable at same paths (verified via `openapi.v2.public.json`)
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
|---|---|
| `backend/app/routes/api.py` (68.5K) | Split into 5 domain routers |
| `backend/app/services/*.py` (43 files) | Moved into domain packages, consolidated where duplicated |
| `backend/app/runtime.py` | Replaced by DI via `Depends()` |
| `backend/main.py` (root) | Kept as standalone merkle/telemetry service |
| `frontend/` (vanilla JS) | Frozen — no new development |
| `bridge_defi/frontend/` | Becomes the unified frontend |
| `backend/app/main.py` | Becomes pure app factory |
