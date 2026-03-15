# Full scan: CUDA, GGUF, Hospital-in-a-box, DB, API docs

**Scanned:** 2026-03-15  
**Scope:** Repository root and subdirs (backend, frontend, docs, scripts, worker, config, etc.)

---

## 1. CUDA

| Location | Finding |
|----------|---------|
| **README.md** (line 74) | Single reference: note that if you have a CUDA GPU and want GPU-enabled PyTorch, follow https://pytorch.org/ for the correct CUDA-enabled package. |
| **Elsewhere** | No other CUDA references (no CUDA runtime checks, no GPU-specific code paths). |

**Summary:** CUDA is only mentioned in README as an optional PyTorch install note. No GGUF or llama.cpp-style model loading in this repo.

---

## 2. GGUF

| Search | Result |
|--------|--------|
| `gguf`, `GGUF` (case-insensitive) | **No matches** in the repository. |

**Summary:** No GGUF model format or related tooling (e.g. llama.cpp, quantized LLM loaders) in this codebase.

---

## 3. Hospital in a box

| Search | Result |
|--------|--------|
| `hospital`, `in a box`, `hospital-in-a-box` (case-insensitive) | **No matches** in the repository. |

**Summary:** No “hospital in a box” product name, docs, or references in this repo.

---

## 4. Databases and storage

### 4.1 Redis

| Location | Usage |
|----------|--------|
| **backend** | `REDIS_URL` (config.py, runtime.py); `MemoryStore` uses Redis when available (memory_store.py); cortex version uses Redis INCR (cortex.py); contract_listener persists to Redis. |
| **bridge-auth** | Session store: ioredis for nonce, refresh tokens (server.js, routes/auth.js, services/session.js, config.js). |
| **docker-compose.yml**, **infra/docker-compose.yml** | `redis:7-alpine` service; backend env `REDIS_URL=redis://redis:6379/0`. |
| **Docs** | STATUS-AND-CAPABILITIES.md, OPERATIONAL-INTERPRETATION.md, ARCHITECTURE.md, SIWE_AUTH.md, SPINE.md, dataflow.md, SENSORS-WIFI-MOUSE-BOOT.md, KIOSK-SHOWCASE-SYNC-GOOGLE-MCP.md, upgrade_path.md, etc. |

### 4.2 SQLite

| Location | Usage |
|----------|--------|
| **bridge-backend** | SIWE nonce replay protection: “SQLite nonce” (package.json, server.js; sqlite3 in package-lock.json). |
| **config/bridge-wall.config.json** | `sqliteNonce`, `redisSessions` flags and descriptions. |
| **STATUS-AND-CAPABILITIES.md** | sqliteNonce capability; redisSessions. |
| **.snapshots/config.json** | Ignore patterns for `*.db`, `*.sqlite`, `*.sqlite3`, `*.db-shm`, `*.db-wal`, `*.sqlitedb`. |

### 4.3 File-backed / other

| Location | Usage |
|----------|--------|
| **backend/app/services/memory_store.py** | File-backed fallback when Redis is unavailable; “stateful without Redis/Docker”. |
| **backend/app/services/marketplace.py** | Comment: “to a database and integrate escrow/payment flows”. |
| **tools/state/** | verify.cjs, sign.cjs reference `Thumbs.db` (ignore list). |

**Summary:** DB/storage in this repo = **Redis** (sessions, memory, versioning, auth) + **SQLite** (SIWE nonce in bridge-backend) + **file fallback** (MemoryStore). No Postgres, MongoDB, or other DBs found. DB behavior is documented in the docs listed above.

---

## 5. Swift API

| Search | Result |
|--------|--------|
| `swift`, `Swift`, `swift-api`, `api.*swift` (case-insensitive) | **No matches** in the repository. |

**Summary:** No Swift language or “Swift API” product/docs in this repo. If you meant “API docs” in general, see section 6.

---

## 6. API documentation (REST / OpenAPI)

### 6.1 Machine-readable

| File | Description |
|------|-------------|
| **openapi.json** (root) | OpenAPI 3.1.0; title “Bridge AI OS”; paths for `/`, `/api/health`, `/api/state`, and many other `/api/*` endpoints. |

### 6.2 Docs that list or describe API endpoints

| Doc | Content |
|-----|---------|
| **docs/CONTRACTS.md** | Contract list: `/api/health`, `/api/health/extended`, `/api/state`, `/api/state/reducers`, `/api/state/snapshot`, `/api/mission/board`, `/api/skills`, `/api/twin/*`, `/api/speech/*`, `/api/tts`, `/api/ubi/claim`, `/api/marketplace/*`, `/api/sdg/metrics`, etc. |
| **docs/SPINE.md** | State, reducers, mission board, twin endpoints, telemetry, audit/drift, `/api/health/extended`, `/api/state/snapshot`, training, esim. |
| **docs/ARCHITECTURE.md** | High-level API (e.g. `/api/state`, `/api/marketplace`, `/api/twin/*`, proxy to Python). |
| **docs/SIWE_AUTH.md** | `POST /api/auth/siwe`, token usage for `/api/state`, `/api/marketplace/*`. |
| **docs/LIVE-MAP-AND-ORCHESTRATE.md** | `GET /api/live/map`, `GET /api/live/report`, `GET /api/orchestrate/directives`. |
| **docs/FULL-AUDIT-3020-DASHBOARD-TWINS.md** | Full table of frontend modules and their GET/POST API routes (mission, founder-todo, twin, shared-xml, skills, marketplace, twins, ubi, revenue, sdg, bossbots, speech, system comprehension, voice, esim, etc.). |
| **docs/DETERMINATOR-SYSTEM-SPEC.md** | Twin state, `/api/twin/*`, `/api/twins`, `/api/twins/leaderboard`, live map/report. |
| **docs/KIOSK-SHOWCASE-SYNC-GOOGLE-MCP.md** | `/api/health`, `/api/live/report`, `/api/live/map`, mission, founder-todo, twins, sensors. |
| **docs/SENSORS-WIFI-MOUSE-BOOT.md** | `POST/GET /api/sensors/wifi`, `POST/GET /api/sensors/mouse`; sensors in live map/report. |
| **docs/OPERATIONAL-INTERPRETATION.md** | WiFi/mouse POST endpoints. |
| **docs/FRONTEND-AUDIT-UX-UI.md** | Mission board, founder-todo, skills, stub routes. |
| **docs/TWINS-SYNC-AND-WIKI.md** | `/api/twins`, `/api/twins/leaderboard`, `/api/state/snapshot`, `/api/twin/shared-xml`, `/api/twin/env-keys`, `/api/wiki/registry`. |
| **STATUS-AND-CAPABILITIES.md** | Sensors (POST/GET wifi, mouse), capabilities list. |
| **KEYS-REQUIRED.md** | `GET /api/twin/env-keys`, backend routes. |
| **FOUNDER-TODO.md** | Example `PATCH /api/founder-todo/obj-1/complete`. |
| **FETCH_LOG_AUDIT.md** | `/api/health` usage. |
| **docs/CHANGES-FOR-REVIEW.md** | Sensor and storage-sync API references. |

### 6.3 Code that implements or calls the API

| Path | Role |
|------|------|
| **backend/app/routes/api.py** | Defines REST routes (sensors, twin, mission, live, etc.). |
| **frontend/src/api.js** | Frontend API client. |
| **tests/test_api.py** | Backend API tests. |

**Summary:** API is documented in **openapi.json** and in **docs** (especially CONTRACTS.md, SPINE.md, FULL-AUDIT-3020-DASHBOARD-TWINS.md, LIVE-MAP-AND-ORCHESTRATE.md). No separate “Swift API” doc set; the REST API is the main API surface.

---

## 7. Quick reference: where to look

| Topic | Where |
|-------|--------|
| **CUDA** | README.md (PyTorch note only). |
| **GGUF** | Not in repo. |
| **Hospital in a box** | Not in repo. |
| **Redis** | backend (config, memory_store, cortex, contract_listener), bridge-auth, docker-compose, STATUS-AND-CAPABILITIES.md, OPERATIONAL-INTERPRETATION.md, ARCHITECTURE.md, SIWE_AUTH.md, dataflow.md, others. |
| **SQLite** | bridge-backend (nonce), config, STATUS-AND-CAPABILITIES.md, .snapshots/config.json. |
| **Other DBs** | None (no Postgres/Mongo, etc.). |
| **Swift** | Not in repo. |
| **API docs** | **openapi.json**; **docs/CONTRACTS.md**, **docs/SPINE.md**, **docs/FULL-AUDIT-3020-DASHBOARD-TWINS.md**, **docs/LIVE-MAP-AND-ORCHESTRATE.md**, **docs/SIWE_AUTH.md**, plus other docs in section 6.2. |
