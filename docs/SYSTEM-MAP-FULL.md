# Bridge Live Wall — Full System Map

**Generated from codebase and config.** Ports, APIs, services, env, and entry points categorized.

---

## 1. Ports & Services

| Port | Service | Base URL | Health / Notes |
|------|---------|----------|----------------|
| **3000** | Dashboard | http://localhost:3000 | Optional; alt for frontend |
| **3001** | bridge-backend (Node) | http://localhost:3001 | GET /health — SIWE ladder, WebSocket events |
| **3002, 3003, 3010** | bridge-backend alt | — | portRangeFallback / altPorts |
| **3020** | **Frontend (primary)** | http://localhost:3020 | Vite dev or serve; proxies /api, /ws → 8000 |
| **3021** | Frontend alt | http://localhost:3021 | altPort |
| **3022** | Console sync | http://localhost:3022/ | Digital Twin console sync; same content as 3000 console entry |
| **3030** | bridge-auth | http://localhost:3030 | GET /health — SIWE, session, refresh, JWT |
| **3031, 3032, 3040** | Auth / Next.js | — | 3032 = Next.js App (root) |
| **3032** | Next.js App | http://localhost:3032/ | Root app; DASHBOARD_PORT |
| **4201** | Determinator Boot Agent | http://localhost:4201/ | RBAC HRE; system-map.html links all systems |
| **4202** | Taurus Showcase | http://localhost:4202/ | GET /health — gamification, dev support |
| **5173** | Frontend (Vite dev) | http://localhost:5173 | Vite dev server default |
| **6379** | Redis | — | Session/store for bridge-auth |
| **7777** | Installer | — | altPorts 7778, 7779 |
| **8000** | **Bridge API (Python)** | http://localhost:8000 | GET /health, GET / — main backend |
| **8001** | Frontend (Docker host) | — | hostPort when frontend in Docker |
| **8081** | Bridge API (Docker host) | — | hostPort when API in Docker |
| **9229** | Debug | — | Debug port |

**Port registry (config):**  
`3000, 3001, 3002, 3003, 3020, 3021, 3022, 3030, 3031, 3032, 4201, 4202, 5173, 6379, 7777, 7778, 8000, 8001, 8081, 9229`

---

## 2. Production & External URLs

| Role | URL |
|------|-----|
| **Bridge API (deployed)** | https://api.bridge-ai-os.tech |
| **API health** | https://api.bridge-ai-os.tech/health |
| **Gateway (production)** | https://gateway.bridge-ai-os.co.za |
| **Bridge (marketing)** | https://bridge-ai-os.com |
| **SPINE API** | https://spine.bridge-ai-os.com |
| **Email from** | noreply@bridge-ai-os.com |

---

## 3. API Endpoints (Bridge API — port 8000)

All under `http://localhost:8000` (or `https://api.bridge-ai-os.tech`). Prefix `/api` unless noted.

### 3.1 Root & Health (no /api prefix)

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Service metadata, docs, spine, state_version |
| GET | /health | status, service, port |
| GET | /api/health | Health (router) |
| GET | /api/health/extended | Extended health |

### 3.2 Auth (bridge-auth 3030 + backend)

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/siwe | SIWE login; verify signature, nonce, issue JWT |
| POST | /api/auth/refresh | Refresh token (bridge-auth) |
| GET | /api/auth/verify | Verify token (bridge-auth) |

### 3.3 State & Cortex

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/state | State mutation via sanctioned reducers (SPINE) |
| GET | /api/state/snapshot | Full state snapshot |
| GET | /api/state/reducers | Sanctioned reducers registry |
| GET | /api/capabilities | Capability flags for twins |
| GET | /api/telemetry | Observability metrics |

### 3.4 Twin & Cognitive

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/twin/shared-xml | Shared canonical XML (mission, authority) |
| POST | /api/twin/shared-xml | Update shared XML |
| GET | /api/twin/profile | Cognitive twin profile |
| GET | /api/twin/env-keys | Env/API keys status (for Twin panel) |
| POST | /api/twin/decide | Twin decide |
| POST | /api/twin/simulate | Twin simulate |
| POST | /api/twin/evolve | Twin evolve |

### 3.5 Mission & Skills

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/mission/board | Mission board counts (backlog, in_progress, review, done) |
| POST | /api/skills | Add skill (name, tags, description) |

### 3.6 User & Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/user/settings | User settings |
| PUT | /api/user/settings | Update user settings |

### 3.7 Emotion & Governance

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/emotion/compute | Compute emotion (votes, backlog, sentiment) |

### 3.8 UBI & SDG

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/ubi/claim | Claim UBI (address) |
| GET | /api/sdg/metrics | SDG metrics (UBI claims, tasks, trades) |

### 3.9 Marketplace & Tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/marketplace/tasks | List tasks |
| POST | /api/marketplace/task | Create task |
| POST | /api/marketplace/pledge | Pledge to task |
| POST | /api/marketplace/accept | Accept task |
| POST | /api/marketplace/complete | Complete task |

### 3.10 Twins Competition & Teaching

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/twins | List twins |
| GET | /api/twins/leaderboard | Leaderboard |
| POST | /api/twins/auto-add | Auto-add task for competition |
| POST | /api/twins/allocate | Allocate task to twin |
| POST | /api/twins/teach | Twin teaches twin (skill) |

### 3.11 Boss Bots & Revenue

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/bossbots/trade | Execute trade (asset) |
| GET | /api/bossbots/signals | Trade signals |
| GET | /api/revenue/status | Revenue engines (balance, UBI, treasury, ops, founder) |

### 3.12 Live Map & Orchestration

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/live/map | Live map (services, ports) |
| GET | /api/live/report | Live report (twins, leaderboard, report_at) — poll for dashboard |
| GET | /api/orchestrate/directives | Orchestration directives |

### 3.13 Replication

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/replication/status | Replication status |
| GET | /api/replication/nodes | Replication nodes |
| POST | /api/replication/register | Register node (node_id, url) |

### 3.14 Sensors

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/sensors/wifi | Ingest WiFi RF sensor |
| GET | /api/sensors/wifi | Get WiFi sensor state |
| POST | /api/sensors/mouse | Ingest mouse tracker |
| GET | /api/sensors/mouse | Get mouse sensor state |

### 3.15 Speech & TTS

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/speech/reason | Speech reasoning |
| POST | /api/speech/embody | Speech embody (text → reasoning) |
| POST | /api/speech/embody/speak | TTS + phonemes/visemes (canonical for avatar) |
| GET | /api/speech/embodiment/skill | Skill definition |
| POST | /api/speech/embodiment/memory/clear | Clear embodiment memory |
| GET | /api/speech/embodiment/memory | Get embodiment memory |
| GET | /api/tts/available | Available TTS voices |
| POST | /api/tts | Raw TTS stream (deprecation: prefer /api/speech/embody/speak) |

### 3.16 System Comprehension

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/system/comprehension | System comprehension payload |
| GET | /api/system/comprehension/explain | Explain (level) |
| GET | /api/system/comprehension/operational-model | Operational model |
| GET | /api/system/comprehension/role-awareness | Role awareness |
| POST | /api/system/comprehension/check-alignment | Check alignment (action, context) |
| POST | /api/system/comprehension/evolve | Evolve system comprehension |
| GET | /api/system/comprehension/skill | Skill definition |

### 3.17 Training & E-Sim

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/train/start | Start training |
| GET | /api/train/status | Training status |
| GET | /api/esim/status | E-sim status (stub) |

### 3.18 Wiki & Audit

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/wiki/registry | Wiki twin registry |
| GET | /api/audit/drift | Audit drift score |

### 3.19 Founder & Human

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/founder-todo | Founder todo list |
| PATCH | /api/founder-todo/{obj_id}/complete | Mark founder todo complete |
| GET | /api/human | Human API info (for console sync) |

### 3.20 WebSocket

| Protocol | Path | Description |
|----------|------|-------------|
| WS | /ws/{channel} | Real-time channel (heartbeat, state mutations) |

---

## 4. Frontend Entry Points (port 3020 / 5173)

| Path | Description |
|------|-------------|
| / | Main app (index.html) — Digital Twin, panels, gateway |
| /index.html | Same |
| /50-applications.html | 50 Applications page |
| /executive-dashboard.html | Executive dashboard (D3 heatmap, swarm) |
| /agents.html | Agents & Twins; live report |
| /docs.html | Docs & wiki links; API table |
| /gateway/ | Gateway (QR join) |
| /join.html | Join as Agent |
| /landing.html | Landing |
| /settings.html | Settings (API base, keys) |
| /digital-twin-console.html | Redirect to console sync URL (3022 or __CONSOLE_SYNC_URL) |

**Vite proxy (dev):** `/api` → http://localhost:8000, `/ws` → ws://localhost:8000

---

## 5. Other Services (Determinator 4201, Taurus 4202)

### Determinator Boot Agent (4201)

- **System Map:** http://localhost:4201/system-map.html — links to Bridge API, Frontend, Gateway, Join, Agents, Dashboard, Docs, 50 Apps, Next.js 3032, Taurus, Console 3022, Production API.
- **Env:** `DETERMINATOR_NEXT_URL` (default http://localhost:8000), `FRONTEND_URL` (default http://localhost:3020), `PORT` (4201).

### Taurus Showcase (4202)

- **Health:** GET http://localhost:4202/health
- **Storage sync:** GET /api/storage-sync (Google Drive / Sheet / local Excel)
- Links to Bridge API endpoints (twins, leaderboard, mission, founder-todo, live/map, live/report).

---

## 6. Environment Variables & API Keys

### Critical (from .env.example)

| Key | Purpose |
|-----|---------|
| OPENAI_API_KEY | OpenAI |
| HF_TOKEN | Hugging Face (primary) |
| HUGGING_FACE_API_KEY | Hugging Face (alt) |
| CLOUDFLARE_ACCOUNT_ID | Cloudflare |
| JWT_SECRET | JWT (bridge) |
| JWT_SECRET_KEY | JWT key |

### Optional

| Key | Purpose |
|-----|---------|
| TURNSTILE_SECRET_KEY | Cloudflare Turnstile |
| ELEVENLABS_API_KEY | ElevenLabs TTS |
| ANTHROPIC_API_KEY | Anthropic |
| SMTP_PASSWORD | SMTP |
| PAYPAL_CLIENT_ID | PayPal |
| DISCORD_BOT_TOKEN | Discord bot |
| R2_BUCKET_NAME | Cloudflare R2 |

### Bridge-specific

| Key | Purpose |
|-----|---------|
| BRIDGE_SIWE_JWT_SECRET | SIWE JWT (bridge-auth) |
| BRIDGE_LIVE_WALL_PATH | Repo path (e.g. E:\BridgeAI\BridgeLiveWall) |
| BRIDGE_API_URL | API base (e.g. https://bridge-ai-os.com) |
| REDIS_URL | Redis (bridge-auth sessions) |
| BRIDGE_SIWE_ALLOWED_DOMAINS | SIWE allowed domains |
| BRIDGE_SIWE_RPC_URL | Chain RPC |
| BRIDGE_SIWE_CHAIN_ID | Chain ID |
| BRIDGE_SIWE_REQUIRE_ROLE | Require on-chain role |
| BRIDGE_SIWE_ROLE_CONTRACT | Role contract address |
| BRIDGE_AUTH_PORT | bridge-auth port (3030) |
| DETERMINATOR_NEXT_URL | Determinator redirect (default http://localhost:8000) |
| FRONTEND_URL | Frontend base (e.g. http://localhost:3020) |
| BRIDGE_API_URL / BRIDGE_LIVE_WALL_PATH | Sensors (wifi-rf, mouse-tracker) POST to API |

**Env load order (backend):** repo `.env` → `E:\AOE\.env` → `E:\AOE\v1\.env`  
**Config drive paths:** `config/bridge-wall.config.json` → `drives.E`, `drives.C`, `drives.D`, `envSearchOrder`

---

## 7. Config Files

| File | Purpose |
|------|---------|
| config/bridge-wall.config.json | Ports, services, modules, API base URLs, drives, twinsSync, sensors, pbootsAndRuns |
| frontend/vite.config.js | Dev server 3020, proxy /api, /ws to 8000; stub routes when backend down |
| frontend/src/config.js | API_BASE, WS_BASE (window.__API_BASE, __WS_BASE or same-origin) |
| backend/app/config.py | Backend config |
| bridge-auth/config.js | Auth service config |
| .env, .env.example | Env and API keys |

---

## 8. Drive Paths (E/C/D)

From `config/bridge-wall.config.json`:

- **E:** E:\AOE, E:\AOE\.env, E:\AOE\v1\.env, E:\BridgeAI\BridgeLiveWall, data, logs  
- **C:** Users, Downloads, AppData, .aws, Program Files, ProgramData  
- **D:** D:\BridgeAI\data, logs, backup, workspaceAlt  

---

## 9. Quick Reference — Default Local URLs

```
Bridge API       http://localhost:8000
Frontend         http://localhost:3020   (or 5173 dev)
Console sync     http://localhost:3022
bridge-auth      http://localhost:3030
bridge-backend   http://localhost:3001
Determinator     http://localhost:4201   (system-map.html)
Taurus           http://localhost:4202
Next.js app      http://localhost:3032
Production API   https://api.bridge-ai-os.tech
```

---

*Source: backend/app/main.py, backend/app/routes/api.py, backend/app/routes/auth.py, config/bridge-wall.config.json, frontend vite.config.js, scripts/determinator-boot-agent.js, scripts/taurus-showcase-server.js, .env.example, and repo docs.*
