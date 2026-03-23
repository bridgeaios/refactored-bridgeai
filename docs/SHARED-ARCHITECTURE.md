# Shared Architecture — DB, Spine, Revenue, Centralized Local + Cloud

All Bridge surfaces (Executive Dashboard, Agents, CFO, Network Dashboard, Status, BAN Live Wall, etc.) share:

## 1. Shared DB (MemoryStore)

- **Primary**: Redis (`REDIS_URL`, default `redis://localhost:6379/0`)
- **Fallback**: File-backed `.bridge-state/runtime/memory_store.json` (when Redis unavailable)
- **Used by**: State version, state hash, twin shared XML, boots/runs logs, skills, user settings, wiki registry, SVG build events, sensor data
- **Single source**: All API routes use `app.runtime.memory` — one instance per process

## 2. Shared Spine

- **Flow**: `Endpoint → Reducer → State → Scheduler → Expression`
- **Mutation**: Only via sanctioned reducers (`POST /api/state` with `reducer` + `payload`)
- **No rogue mutation**: No direct state write; all change flows through cortex
- **Exposed**: `GET /api/state/snapshot`, `GET /api/live/report`, capabilities, authority classes

## 3. Shared Revenue

- **RevenueService** → collects from UBI, marketplace, BossBots, sensor tasks
- **TreasuryService** → unified ledger (all projects, one ledger)
- **Buckets**: UBI, Treasury, Ops, Founder
- **API**: `GET /api/revenue/status`, `GET /api/treasury/status`, `GET /api/treasury/ledger`
- **Flow**: `revenue_service.collect()` → `treasury_service.collect()` (callback wired at startup)

## 4. Centralized Local + Cloud

- **Local**: `http://localhost:8000` (Bridge API)
- **Cloud**: `https://api.bridge-ai-os.tech`
- **Switch**: Add `?api=cloud` to any page URL, or set `localStorage.bridge_api_mode = 'cloud'`
- **Config**: `frontend/public/bridge-api-config.js` sets `window.__API_BASE` before page scripts
- **Pages**: Executive Dashboard, Agents, CFO, Network Dashboard, Status, BAN Live Wall use `__API_BASE` when set

## 5. Surfaces That Share

| Surface | DB | Spine | Revenue |
|---------|----|----|---------|
| Executive Dashboard | ✓ | ✓ | ✓ |
| Agents (Cortex) | ✓ | ✓ | ✓ |
| CFO | ✓ | ✓ | ✓ |
| Network Dashboard | ✓ | ✓ | ✓ |
| Status | ✓ | ✓ | ✓ |
| BAN Live Wall | ✓ | ✓ | ✓ |
| Digital Twin Console | ✓ | ✓ | ✓ |

All hit the same Bridge API, which uses the single MemoryStore, single Spine, single Treasury.
