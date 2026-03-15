# Full Audit — localhost:3020, Dashboard, Digital Twins, APIs, Sync & Adaptive GET/POST

**Date:** 2026-03-15  
**Scope:** Frontend (3020), dashboard (3000), digital twin surfaces, API usage, synchronization, adaptive GET/POST patterns.

---

## 1. Frontend (http://localhost:3020/)

### 1.1 Role and stack

- **Port:** 3020 (Vite dev 5173; production serve via `npm run start`).
- **Stack:** Vite, Babylon.js, ES modules; proxies `/api` and `/ws` to Bridge API (8000).
- **Entry:** `index.html` → `src/main.js`; loads 20+ modules (mission board, founder TODO, twin panel, terminal, wallet, marketplace, etc.).

### 1.2 API usage (GET / POST / PATCH) — all via `API_BASE` (same-origin or proxy)

| Module | GET | POST / PATCH | Sync / adaptive |
|--------|-----|---------------|-----------------|
| **missionBoard** | `/api/mission/board` (poll 10s) | — | Fallback to shared XML mission on failure |
| **founderTodo** | `/api/founder-todo` (poll 15s) | `PATCH /api/founder-todo/{id}/complete` | Default TODO on fetch error |
| **twinPanel** | `/api/twin/env-keys`, profile via cognitiveTwin | — | Profile + env keys in one view |
| **cognitiveTwin** | `/api/twin/profile` | `POST /api/twin/decide`, `simulate`, `evolve` | Twin actions (decide/simulate/evolve) |
| **twinSharedXml** | `/api/twin/shared-xml` | `POST /api/twin/shared-xml` | Shared XML sync; `onSharedXmlUpdate` callback |
| **skillsPanel** | — | `POST /api/skills` | Local list + API post |
| **marketplace** | `/api/marketplace/tasks` | `POST task`, `pledge`, `accept`, `complete` | Task list + allocate/complete flow |
| **twinCompetition** | `/api/twins`, `/api/twins/leaderboard`, `/api/marketplace/tasks` | `POST /api/twins/allocate`, `auto-add`, `teach`, `marketplace/complete` | Leaderboard + tasks + allocate/teach |
| **ubi** | — | `POST /api/ubi/claim` | Claim with address |
| **revenue** | `/api/revenue/status` | — | Status display |
| **sdg** | `/api/sdg/metrics` | — | Metrics display |
| **bossbots** | `/api/bossbots/signals` | `POST /api/bossbots/trade` | Signals + trade |
| **speechEmbodiment** | `/api/speech/embodiment/skill`, `memory` | `POST /api/speech/embody`, `embody/speak`, `memory/clear` | Speech + memory |
| **systemComprehension** | `/api/system/comprehension`, `explain`, `operational-model`, `role-awareness`, `skill` | `POST /api/system/comprehension/check-alignment`, `evolve` | System comprehension + alignment |
| **voice** | — | `POST /api/tts` | TTS |
| **esim** | `/api/esim/status` | — | Status |
| **systemVerifier** | `/api/mission/board` (startup) | — | API + WS check → face state ALIVE/DEGRADED/OFFLINE |

### 1.3 Synchronization and adaptive behavior

- **Polling:** Mission board 10s, founder TODO 15s; no exponential backoff.
- **Shared XML:** Single source for twin/mission; `twinSharedXml` GET + POST and `onSharedXmlUpdate` drive mission board fallback and other consumers.
- **Adaptive GET:** `fetchJson` in `api.js` throws on non-JSON or !ok; callers use fallbacks (e.g. mission → shared XML, founder TODO → DEFAULT_TODO).
- **Adaptive POST:** No global retry; errors often only in console. Twin panel shows result for 4s then hides.
- **WebSocket:** Terminal uses `/ws/mission`; reconnects after 15s on close. Emotion/expression driven by WS messages.

### 1.4 Similarities across surfaces

- **Single API base:** All use `API_BASE` ('' when same-origin with proxy). One backend (8000) for all.
- **Digital twin surfaces:** Twin panel, cognitive twin (decide/simulate/evolve), twin competition (twins + leaderboard), shared XML — all map to same twin/state layer.
- **Task/mission:** Mission board, founder TODO, marketplace tasks, twin competition tasks — different GET endpoints but same “task list / progress” idea; could be unified under live map or a single task API.

---

## 2. Dashboard (port 3000)

- **Config:** `config/bridge-wall.config.json` defines `dashboard` on port 3000 (label “Dashboard”).
- **Current state:** No dedicated dashboard app in repo; “Dashboard” is a placeholder port. Frontend (3020) and Taurus Showcase (4202) act as control/showcase surfaces.
- **Similarities with 3020:** Both can consume `/api/live/map`, `/api/live/report` for a unified view. Dashboard could be implemented as a thin client that only polls live report and shows status (same APIs as kiosk).

---

## 3. Digital twin surfaces and APIs

| Surface | Location | GET | POST/PATCH | Sync |
|---------|----------|-----|------------|------|
| **Twin profile / env** | Frontend twinPanel | `/api/twin/profile`, `/api/twin/env-keys` | — | Load profile + keys |
| **Twin decide/simulate/evolve** | Frontend cognitiveTwin + twinPanel | — | decide, simulate, evolve | Result shown in panel |
| **Shared XML** | Frontend twinSharedXml | `/api/twin/shared-xml` | `POST /api/twin/shared-xml` | Global twin/mission state |
| **Twins list / leaderboard** | Frontend twinCompetition | `/api/twins`, `/api/twins/leaderboard` | allocate, auto-add, teach | Leaderboard + tasks |
| **Live map/report** | Any client | `/api/live/map`, `/api/live/report` | — | pboots, runbs, twins, capabilities, sensors |
| **Mission board** | Frontend missionBoard | `/api/mission/board` | — | Backlog / in progress / review / done |
| **Founder TODO** | Frontend founderTodo | `/api/founder-todo` | `PATCH .../complete` | Objectives → wallpaper |

All twin-related state ultimately flows from or through the Bridge API (8000); shared XML and live map are the main sync points for “single source of truth.”

---

## 4. Where APIs and similarities apply

- **Unified read:** `/api/live/report` (or `/api/live/map`) gives one payload for: pboots, runbs, state version, twins, leaderboard, capabilities, telemetry, services, **sensors** (wifi, mouse). Frontend (3020), dashboard (3000), kiosk, and Taurus Showcase can all use it for a consistent view.
- **Unified twin:** `/api/twin/*` (profile, env-keys, shared-xml, decide, simulate, evolve) and `/api/twins`, `/api/twins/leaderboard` — same backend; frontend and any future dashboard/twin UI should share these.
- **Sync:** Shared XML + mission board + founder TODO + live map form a sync story: config/tasks/mission can be read from one place (live map) or from dedicated endpoints; writes go through POST/PATCH to API.
- **Adaptive GET/POST:** Use `fetchJson` and fallbacks (shared XML, default TODO); add retry or user-visible errors for POST where needed.

---

## 5. Goals and tasks (goal = task = goal)

Goals and tasks are aligned so that each **goal** maps to one or more **tasks**, and completing the task(s) satisfies the goal (goal = task = goal).

| Goal | Task(s) | Outcome |
|------|---------|---------|
| Install all deps | Run `install-all.ps1` | Python + bridge-backend + frontend npm install |
| Build frontend | Run `npm run build` in frontend | State verify + Vite build → dist/ |
| Audit system | Run `audit-wall.ps1` | audit-results.json; 0 critical target |
| Apply keys | Run `apply-keys.ps1` | .env from .env.example if missing |
| State verify | Run `node tools/state/verify.cjs` | Merkle/identity match or approve |
| Debug (tests) | Run `pytest tests/` | 27/27 pass target |
| Deploy edge | Run worker deploy (e.g. setup-r2-and-deploy or wrangler deploy) | api.bridge-ai-os.tech live |
| Full run (install → deploy) | Run `run-full-install-build-deploy.ps1` | Install → build → debug → deploy + log |

Full log scan and goal/task tracking are in the run script and `data/goals-tasks.json` (see below).

---

## 6. References

- **Frontend UX/UI audit:** `docs/FRONTEND-AUDIT-UX-UI.md`
- **Operational interpretation:** `docs/OPERATIONAL-INTERPRETATION.md`
- **Config:** `config/bridge-wall.config.json`
- **API routes:** `backend/app/routes/api.py`; live map includes `sensors` (wifi, mouse).
