# Digital Twin Blueprint — Bridge AI OS (BridgeLiveWall)
*Generated: 2026-03-16 | Mode: Autonomous Bootstrap | Branch: win-for-twin*

---

## Project Identity

| Field | Value |
|-------|-------|
| Project_ID | bridge-ai-os-livewall |
| Project_Name | Bridge AI OS — BridgeLiveWall |
| Local_Path | E:\BridgeAI\BridgeLiveWall |
| Languages | Python 3.11, JavaScript (ESM + CJS), TypeScript (bridge_defi frontend) |
| Frameworks | FastAPI + Uvicorn (backend), Vite + Babylon.js + Three.js (frontend), Node.js HTTP (Determinator), Cloudflare Workers (edge) |
| Deployment_Type | Docker Compose (local/VPS), Cloudflare Worker (edge/API), GitHub Actions CI |
| Status | Active — development branch `win-for-twin` |
| Production API | https://api.bridge-ai-os.tech |
| Pricing Model | Starter $499/mo · Growth $799/mo |
| Revenue Target | $17K MRR → $50K MRR |

---

## Infrastructure Registry

| Service | Type | Port (host:container) | Config File | Status |
|---------|------|-----------------------|-------------|--------|
| backend (FastAPI) | Python API | 8081:8000 | docker-compose.yml | Configured (Docker) / local port 8000 |
| frontend (Vite) | Static/SSR | 8001:3000 | docker-compose.yml | Configured (Docker) / local port 3020 |
| redis | Cache / Message Bus | 6379:6379 | docker-compose.yml | Configured |
| prometheus | Metrics | 9090:9090 | docker-compose.yml + prometheus.yml | Configured |
| grafana | Dashboards | 3001:3000 | docker-compose.yml | Configured |
| neo4j | Graph DB | 7474:7474, 7687:7687 | docker-compose.yml | Configured |
| determinator-boot-agent | Node HTTP server | 4201 | scripts/determinator-boot-agent.js | Configured |
| taurus-showcase | Node HTTP server | 4202 | scripts/taurus-showcase-server.js | Configured |
| bridge-backend | Node.js (SIWE/SQLite) | 3001 | bridge-backend/server.js | Optional / configured |
| bridge-auth | Node.js (JWT/Redis) | 3030 | bridge-auth/server.js | Optional / configured |
| nextjs-app | Next.js | 3032 | config/bridge-wall.config.json | Reference (external AOE repo) |
| Cloudflare Worker | Edge worker | — | worker/wrangler.toml | Deployed at api.bridge-ai-os.tech |
| Cloudflare R2 | Object storage | — | worker/wrangler.toml | Binding: `bridge-live-wall` bucket |

**Volumes (Docker):** `prometheus_data`, `grafana_data`, `neo4j_data`, `neo4j_logs`

---

## Domain & Routing Map

| Domain | Target / Purpose | Config Source |
|--------|-----------------|---------------|
| bridge-ai-os.com | PRIMARY — Economic engine landing | CLAUDE.md |
| bridge-ai-os.co.za | ALIAS → bridge-ai-os.com (SA variant) | CLAUDE.md |
| bridge-ai-os.org | ALIAS → bridge-ai-os.com | CLAUDE.md |
| bridge-ai-os.tech | ALIAS → bridge-ai-os.com | CLAUDE.md |
| api.bridge-ai-os.tech | Cloudflare Worker — Bridge API edge endpoint | worker/wrangler.toml |
| gateway.bridge-ai-os.co.za | Public gateway endpoint | CLAUDE.md |
| ai-os.co.za | Internal financial ops (Zero Trust) | CLAUDE.md |
| supaco.ai | PRIMARY — Supaco API + Auth (JWT) | CLAUDE.md |
| supaco.io | ALIAS → supaco.ai (marketing) | CLAUDE.md |
| supaco.co.za | ALIAS → supaco.ai (SA variant) | CLAUDE.md |

**API Route Prefixes (FastAPI at :8000):**

| Prefix | Router File | Purpose |
|--------|-------------|---------|
| /api/* | backend/app/routes/api.py | Core twin, marketplace, sensors, speech, live map |
| /api/auth/* | backend/app/routes/auth.py | SIWE, JWT auth |
| /api/projects/* | backend/app/routes/projects.py | Project registry (register, list, heartbeat) |
| /api/treasury/* | backend/app/routes/treasury.py | Unified treasury collect + status |
| /api/payments/webhook/* | backend/app/routes/treasury.py | Paystack / PayPal / crypto webhooks |
| /api/state | backend/app/main.py | State mutation via sanctioned reducers |
| /api/state/snapshot | backend/app/main.py | Full state snapshot |
| /api/state/reducers | backend/app/main.py | List sanctioned reducers |
| /api/capabilities | backend/app/main.py | Capability registry |
| /api/telemetry | backend/app/main.py | Observability metrics |
| /ws/{channel} | backend/app/main.py | WebSocket channels |
| /health | backend/app/main.py | Root health check |
| /gateway | backend/app/main.py (ref) | Gateway metadata |

---

## Service Registry

| Service | Port | Start Command | Health Endpoint | Status |
|---------|------|---------------|-----------------|--------|
| Bridge API (local) | 8000 | `.\run-backend.ps1` or `uvicorn app.main:app --reload --port 8000` | GET /health | Configured |
| Bridge API (Docker) | 8081 | `docker-compose up backend` | GET /health | Configured |
| Frontend (local dev) | 5173 | `cd frontend && npm run dev` | — | Configured |
| Frontend (local prod) | 3020 | `cd frontend && npm start` | — | Configured |
| Frontend (Docker) | 8001 | `docker-compose up frontend` | — | Configured |
| Determinator Boot Agent | 4201 | `node scripts/determinator-boot-agent.js` or `.\scripts\serve-determinator-boot.ps1` | GET /health | Configured |
| Taurus Showcase | 4202 | `node scripts/taurus-showcase-server.js` or `.\scripts\serve-taurus-showcase.ps1` | GET /health | Configured |
| bridge-backend | 3001 | `cd bridge-backend && node server.js` | GET /health | Optional/configured |
| bridge-auth | 3030 | `cd bridge-auth && node server.js` | GET /health | Optional/configured |
| Redis | 6379 | `docker-compose up redis` | — | Configured |
| Prometheus | 9090 | `docker-compose up prometheus` | — | Configured |
| Grafana | 3001 (Docker 3001:3000) | `docker-compose up grafana` | — | Configured |
| Neo4j | 7474 / 7687 | `docker-compose up neo4j` | — | Configured |
| Cloudflare Worker | — | `npx wrangler deploy` (from worker/) | GET / or /health | Configured (deployed) |
| Console Sync | 3022 | config/bridge-wall.config.json reference | — | Reference only |

**Local URL Map:**

| Service | URL |
|---------|-----|
| System Map | http://localhost:4201/system-map.html |
| Determinator (RBAC) | http://localhost:4201/ |
| Bridge API | http://localhost:8000 |
| Frontend (Digital Twin) | http://localhost:3020/ |
| Gateway (QR join) | http://localhost:3020/gateway/ |
| Join as Agent | http://localhost:3020/join.html |
| Executive Dashboard | http://localhost:3020/executive-dashboard.html |
| 50 Applications | http://localhost:3020/50-applications.html |
| Agents & Twins | http://localhost:3020/agents.html |
| Docs | http://localhost:3020/docs.html |
| Taurus | http://localhost:4202/ |
| Grafana | http://localhost:3001 (Docker) |
| Prometheus | http://localhost:9090 |
| Neo4j Browser | http://localhost:7474 |
| Production API | https://api.bridge-ai-os.tech |

---

## External Integrations

| Service | Provider | Purpose | Integration File(s) |
|---------|----------|---------|---------------------|
| OpenAI | OpenAI | AI inference (enabled in config) | config/bridge-wall.config.json, backend/app/routes/api.py (OPENAI_API_KEY check) |
| Anthropic | Anthropic | AI inference (optional, disabled by default) | config/bridge-wall.config.json, backend/app/routes/api.py (ANTHROPIC_API_KEY check) |
| Hugging Face | HF | AI models (enabled in config) | backend/app/routes/api.py (HF_TOKEN, HUGGING_FACE_API_KEY checks) |
| ElevenLabs | ElevenLabs | TTS voice synthesis | config/bridge-wall.config.json, backend/app/services/voice_broker.py, backend/app/routes/api.py (ELEVENLABS_API_KEY) |
| JWT Auth | PyJWT | Session tokens | backend/requirements.txt, backend/app/services/siwe_auth.py |
| SIWE | Sign-In with Ethereum | Web3 wallet auth | backend/app/services/siwe_auth.py, bridge-auth/server.js |
| Paystack | Paystack | Payment webhooks (SA/Africa) | backend/app/services/payment_rails.py, backend/app/routes/treasury.py |
| PayPal | PayPal | Payment webhooks (global) | backend/app/services/payment_rails.py, backend/app/routes/treasury.py |
| Crypto (BRDG) | On-chain | Bridge token payments | backend/app/services/payment_rails.py, backend/app/services/contract_listener.py |
| Prometheus | CNCF | Metrics scraping | prometheus.yml, backend/app/services/telemetry.py |
| Grafana | Grafana Labs | Dashboard visualization | docker-compose.yml, docs/grafana-dashboard-swarm.json |
| Cloudflare Workers | Cloudflare | Edge API deployment | worker/wrangler.toml |
| Cloudflare R2 | Cloudflare | Object storage | worker/wrangler.toml (binding: BUCKET / bridge-live-wall) |
| Redis | Redis | Sessions, message bus, state | docker-compose.yml, backend/app/services/swarm_message_bus.py |
| Neo4j | Neo4j | Knowledge graph (agent/skill mapping) | docker-compose.yml, backend/app/services/knowledge_graph.py, backend/app/services/neo4j_connection.py |
| Web3/viem | wagmi/viem | Ethereum wallet interaction | frontend/package.json |
| BabylonJS | BabylonJS | 3D Digital Twin avatar rendering | frontend/package.json |
| Solana Web3.js | Solana | Solana wallet support | frontend/package.json |
| Transak SDK | Transak | Fiat on-ramp | frontend/package.json |
| Google Drive | Google | System Map sync | scripts/google-storage-sync.ps1, scripts/google-storage-sync.sh |
| Discord Bot | Discord | Notifications (optional, disabled) | config/bridge-wall.config.json, DISCORD_BOT_TOKEN env |
| SMTP | Generic | Email (optional, disabled) | config/bridge-wall.config.json, SMTP_PASSWORD env |
| AWS CLI | AWS | Cloud ops (optional, disabled) | config/bridge-wall.config.json |

---

## Code Module Registry

### Backend (Python / FastAPI)

| Module ID | Path | Language | Purpose | Key Dependencies |
|-----------|------|----------|---------|-----------------|
| main | backend/app/main.py | Python | FastAPI app entry, lifespan, CORS, WebSocket hub, middleware | FastAPI, all routes, cortex, physics, runtime |
| api_router | backend/app/routes/api.py | Python | Core API: twin, marketplace, sensors, speech, live map, replication, SDG, revenue, bossbots | cortex, physics, runtime services |
| auth_router | backend/app/routes/auth.py | Python | SIWE + JWT authentication | siwe_auth service |
| projects_router | backend/app/routes/projects.py | Python | Project registry: register, list, heartbeat, deregister | projects service |
| treasury_router | backend/app/routes/treasury.py | Python | Unified treasury collect, status, payment webhooks | treasury service, payment_rails |
| cortex | backend/app/cortex.py | Python | Authority, capability flags, state version, boot/run logging, sensor state | Redis memory |
| physics | backend/app/physics.py | Python | Determinism, drift, ethics, economic risk governor, identity seal, telemetry | numpy |
| runtime | backend/app/runtime.py | Python | Service singletons (all services instantiated here) | All service modules |
| reducers | backend/app/reducers.py | Python | Sanctioned reducer registry, strict mode, identity hash | — |
| models | backend/app/models/ | Python | Pydantic models | pydantic |
| cognitive_twin | backend/app/services/cognitive_twin.py | Python | Decision engine, behavioral simulation, evolution loop | physics |
| emotion | backend/app/services/emotion.py | Python | Emotion computation service | — |
| learning | backend/app/services/learning.py | Python | Model training loop (emotion fine-tuning) | — |
| memory_store | backend/app/services/memory_store.py | Python | Redis-backed KV memory abstraction | redis |
| mission | backend/app/services/mission.py | Python | Mission board (backlog/in_progress/review/done) | memory_store |
| mission_economy | backend/app/services/mission_economy.py | Python | Economic mission layer | — |
| marketplace | backend/app/services/marketplace.py | Python | Task marketplace (create, pledge, accept, complete) | — |
| revenue | backend/app/services/revenue.py | Python | Revenue collection + auto-split (UBI 40%, Treasury 30%, Ops 20%, Founder 10%) | asyncio |
| treasury | backend/app/services/treasury.py | Python | Unified treasury (multi-project, by-currency, by-method) | — |
| payment_rails | backend/app/services/payment_rails.py | Python | Paystack, PayPal, crypto webhook verification + parsing | hashlib, hmac |
| projects | backend/app/services/projects.py | Python | Project registry service (seed, register, list) | — |
| replication | backend/app/services/replication.py | Python | Twin replication engine + node discovery (mesh) | memory_store |
| ubi | backend/app/services/ubi.py | Python | Universal Basic Income distribution | — |
| twins_competition | backend/app/services/twins_competition.py | Python | Twin leaderboard, task allocation, skill teaching | marketplace |
| bossbots | backend/app/services/bossbots.py | Python | BossBot trading signal generation + twin execution | revenue |
| sdg | backend/app/services/sdg.py | Python | SDG (Sustainable Dev Goals) metric tracking | — |
| speech_embodiment | backend/app/services/speech_embodiment.py | Python | Full speech pipeline: LLM → TTS → phonemes → visemes | voice_broker |
| speech_reasoning | backend/app/services/speech_reasoning.py | Python | ASR transcript processing, intent, emotion, response | — |
| voice_broker | backend/app/services/voice_broker.py | Python | TTS provider abstraction (ElevenLabs) | httpx/aiohttp |
| telemetry | backend/app/services/telemetry.py | Python | Prometheus metrics: agent latency, decisions, swarm health, drift, entropy | prometheus_client |
| swarm_message_bus | backend/app/services/swarm_message_bus.py | Python | Redis pub/sub inter-agent communication bus | redis.asyncio |
| knowledge_graph | backend/app/services/knowledge_graph.py | Python | In-memory skill/agent graph, collaboration discovery | — |
| neo4j_connection | backend/app/services/neo4j_connection.py | Python | Neo4j driver connection (untracked — not yet committed) | neo4j driver |
| evolution_governance | backend/app/services/evolution_governance.py | Python | Mutation proposals, quarantine, governance voting | — |
| blockchain | backend/app/services/blockchain.py | Python | Blockchain interaction layer | web3 |
| contract_listener | backend/app/services/contract_listener.py | Python | On-chain event listener (background task) | web3 |
| siwe_auth | backend/app/services/siwe_auth.py | Python | SIWE (Sign-In with Ethereum) auth | eth-account, PyJWT |
| automation | backend/app/services/automation.py | Python | AutomationLoops: background task scheduler | asyncio |
| system_comprehension | backend/app/services/system_comprehension.py | Python | Structural mapping, alignment filter, operational model | — |
| esim | backend/app/services/esim.py | Python | eSIM service | — |
| governance | backend/app/services/governance.py | Python | Governance layer | — |
| websocket_manager | backend/app/websocket_manager.py | Python | WebSocket connection manager | — |
| websockets/hub | backend/app/websockets/hub.py | Python | ConnectionManager: broadcast, heartbeat | — |

### Frontend (Vite / JavaScript)

| Module ID | Path | Language | Purpose | Key Dependencies |
|-----------|------|----------|---------|-----------------|
| frontend-main | frontend/public/main.js | JavaScript | Main app entry | BabylonJS, Three.js |
| cognitiveTwin | frontend/public/cognitiveTwin.js | JavaScript | Digital Twin UI logic | — |
| babylonRenderer | frontend/public/babylonRenderer.js | JavaScript | 3D avatar rendering | @babylonjs/core |
| bridgeUi | frontend/public/bridgeUi.js | JavaScript | Bridge UI components | — |
| emotionEngine | frontend/public/emotionEngine.js | JavaScript | Emotion state UI | — |
| bossbots | frontend/public/bossbots.js | JavaScript | BossBot UI | — |
| founderTodo | frontend/public/founderTodo.js | JavaScript | Founder TODO wallpaper integration | — |
| lipsync | frontend/public/lipsync.js | JavaScript | Viseme/lipsync driver | — |
| api | frontend/public/api.js | JavaScript | API client to Bridge API :8000 | — |
| config | frontend/public/config.js | JavaScript | Frontend config | — |
| 50-applications | frontend/50-applications.html | HTML | 50 AI applications showcase | — |
| executive-dashboard | frontend/public/executive-dashboard.html | HTML | Executive dashboard | — |
| agents | frontend/public/agents.html | HTML | Agents & Twins page | — |
| gateway | frontend/public/gateway/ | HTML | QR join gateway | — |
| join | frontend/public/join.html | HTML | Join as Agent page | — |
| digital-twin-console | frontend/public/digital-twin-console.html | HTML | Twin console sync (port 3022) | — |
| bridge_defi frontend | bridge_defi/frontend/ | TypeScript | DeFi frontend (Vite + TS) | vite, tsconfig |

### Scripts / Agents

| Module ID | Path | Language | Purpose |
|-----------|------|----------|---------|
| determinator-boot-agent | scripts/determinator-boot-agent.js | Node.js | RBAC login → next URL; System Map at /system-map.html |
| taurus-showcase-server | scripts/taurus-showcase-server.js | Node.js | Taurus showcase server :4202 |
| wifi-rf-boot | scripts/wifi-rf-boot.ps1 | PowerShell | WiFi RF sensor → POST /api/sensors/wifi |
| mouse-tracker-boot | scripts/mouse-tracker-boot.ps1 | PowerShell | Mouse tracker → POST /api/sensors/mouse |
| sync-twins-wiki | scripts/sync-twins-wiki.ps1 | PowerShell | Sync digital twins + Downloads → data/twin-registry.json |
| google-storage-sync | scripts/google-storage-sync.ps1 | PowerShell | Sync system-map with Google Drive |
| port-handler | scripts/port-handler.ps1 | PowerShell | List/kill port processes |
| start-recommended-services | scripts/start-recommended-services.ps1 | PowerShell | Start bridge-auth + frontend + dashboard |
| serve-determinator-boot | scripts/serve-determinator-boot.ps1 | PowerShell | Launch Determinator on :4201 |
| audit-wall | audit-wall.ps1 | PowerShell | Full system audit (keys, ports, DNS, drives) |
| run-backend | run-backend.ps1 | PowerShell | Start Bridge API |

### Cloudflare Worker

| Module ID | Path | Language | Purpose |
|-----------|------|----------|---------|
| bridge-live-wall-api | worker/src/index.js | JavaScript (ESM) | Edge worker: health check, R2 list |
| wrangler config | worker/wrangler.toml | TOML | Deployment: name=bridge-live-wall-api, domain=api.bridge-ai-os.tech, R2 bucket binding |

---

## Deployment Pipeline

### CI/CD — GitHub Actions (`.github/workflows/ci.yml`)

Triggers: push to `main` or `win-for-twin`; PRs to `main`

```
Job: test (ubuntu-latest)
  1. actions/checkout@v4
  2. Setup Python 3.11
  3. pip install -r backend/requirements.txt + requirements-test.txt
  4. ruff check backend/          (linter)
  5. mypy app/                    (type checker)
  6. pytest --cov=app --cov-report=xml   (tests)
  7. docker-compose build         (Docker build validation)

Job: lint-frontend (ubuntu-latest)
  1. actions/checkout@v4
  2. Setup Node.js 20
  3. cd frontend && npm install
  4. cd frontend && npm run build
```

### Local Development Pipeline

```
1. Backend:   .\run-backend.ps1
              → uvicorn app.main:app --reload --port 8000

2. Frontend:  cd frontend && npm run dev   (Vite dev :5173)
              cd frontend && npm start      (prod serve :3020)

3. Determinator: node scripts/determinator-boot-agent.js  (PORT=4201)
                 .\scripts\serve-determinator-boot.ps1

4. Taurus:    node scripts/taurus-showcase-server.js      (PORT=4202)
              .\scripts\serve-taurus-showcase.ps1

5. Docker:    docker-compose up             (full stack)
              docker-compose up backend redis neo4j prometheus grafana
```

### Edge Deployment (Cloudflare Worker)

```
cd worker
npx wrangler deploy
# Set secrets: wrangler secret put CLOUDFLARE_API_TOKEN
# R2 setup: .\scripts\setup-r2-and-deploy.ps1
```

### Frontend State Verification

```
cd frontend && npm run build
→ node ../tools/state/verify.cjs   (pre-build state check)
→ vite build
```

---

## Development Telemetry

### Recent Commits (last 7)

| Hash | Message |
|------|---------|
| eea2874 | feat(backend): add projects registry and unified treasury with revenue routing |
| 17d7767 | docs: add planetary-scale topology docs and fix state verify logs exclusion |
| a717006 | Add replication engine integration and API endpoints |
| bb22826 | Replication engine + node discovery: close loop, test, deploy prep |
| d465144 | Enhance documentation for diagrams and self-expanding network |
| b551702 | Update TWINS-SYNC-AND-WIKI.md to include information about diagrams |
| e41aa24 | Initial commit |

### Branches

| Branch | Type |
|--------|------|
| `win-for-twin` | Active development (current + main) |
| `main` | Same as win-for-twin (remote HEAD → win-for-twin) |
| `remotes/origin/win-for-twin` | Remote tracking |

### Tags

No release tags yet.

### Uncommitted / Staged Work (at scan time)

| File | State |
|------|-------|
| audit-results.json | Modified (staged + unstaged) |
| backend/app/physics.py | Modified (staged) |
| backend/app/services/evolution_governance.py | New file (staged) |
| backend/app/services/knowledge_graph.py | New file (staged) |
| backend/app/services/mission_economy.py | New file (staged) |
| backend/app/services/payment_rails.py | Modified (unstaged) |
| backend/app/services/revenue.py | Modified (unstaged) |
| backend/app/services/swarm_message_bus.py | New file (staged) |
| backend/app/services/telemetry.py | Modified (unstaged) |
| bridge_defi/frontend/package-lock.json | New file (staged) |
| docker-compose.yml | Modified (staged) |
| docs/grafana-dashboard-swarm.json | New file (staged) |
| twin_wall.png | Modified (staged) |
| backend/app/services/neo4j_connection.py | Untracked |
| backend/tests/test_services.py | Untracked |
| prometheus.yml | Untracked |

---

## Monitoring Coverage

### Prometheus (`prometheus.yml`)

| Job | Target | Scrape Interval | Metrics Path |
|-----|--------|-----------------|-------------|
| bridge-backend | backend:8000 | 10s | /metrics |
| redis | redis:6379 | 30s | (default) |

- Rule files: `alerts.yml` (referenced but not found in repo)
- Alertmanager: configured but no targets set
- Remote write: localhost:9090 (self-write loop — likely config placeholder)

### Grafana Dashboard (`docs/grafana-dashboard-swarm.json`)

Dashboard: **Bridge Swarm Telemetry** — Prometheus datasource

| Panel | Metric | Type |
|-------|--------|------|
| Swarm Health Score | `swarm_health_score` | Gauge |
| Drift Detection Score | `drift_detection_score` | Gauge |
| Agent Latency | `agent_latency_seconds` | Time series |
| Active Twins | `active_twins` | Stat |
| State Version | `state_version` | Stat |
| Entropy Score | `entropy_score` | Gauge |
| Decision Count | `agent_decisions_total` | Counter |
| Message Queue Depth | `message_queue_depth` | Gauge |

### Application-level Telemetry (`/api/telemetry`)

Tracked in `backend/app/physics.py` (in-process):
- `decision_latency_ms` — P95 latency
- `silence_rate` — ethical silence ratio
- `state_mutation_count` / `failed_mutation_count`
- `economic_conversion_rate`
- `speech_latency_ms`

Tracked in `backend/app/services/telemetry.py` (Prometheus):
- `agent_latency_seconds` (Histogram, by agent_id + task_type)
- `agent_decisions_total` (Counter, by agent_id + decision_type + outcome)
- `agent_cpu_percent` / `agent_memory_mb` (Gauge)
- `agent_heartbeat_seconds` (Gauge)
- `swarm_latency_p50/p99_seconds`
- `message_queue_depth` (by channel)
- `swarm_health_score`
- `drift_detection_score` (by agent_id)
- `failure_detection_seconds` / `recovery_time_seconds`
- `active_twins`, `state_version`, `entropy_score`

---

## Digital Twin State

### Live System State Synthesis

The Digital Twin is the system's self-model. The canonical state lives in Redis and is readable via `/api/state/snapshot`. Key state components:

| State Layer | Storage | Endpoint |
|-------------|---------|---------|
| Canonical state version | Redis (`state:version`) | GET /api/state/snapshot |
| Shared XML (twin authority doc) | Redis (`twin:shared_xml`) | GET /api/twin/shared-xml |
| Mission board (kanban) | Redis | GET /api/mission/board |
| Twin registry | data/twin-registry.json (file) | GET /api/wiki/registry |
| Project registry | Redis (in-memory + seeded from config) | GET /api/projects |
| Revenue / treasury state | In-memory (RevenueService + TreasuryService) | GET /api/revenue/status, GET /api/treasury/status |
| Boots log / runs log | Redis | GET /api/live/map |
| Sensor state (WiFi, mouse) | Redis | GET /api/sensors/wifi, GET /api/sensors/mouse |
| Skills | Redis (`skills` list) | GET /api/skills |
| User settings | Redis (per user-id) | GET /api/user/settings |
| Replication nodes | Redis | GET /api/replication/nodes |

### Service Configuration vs Runtime Gap

| Service | Configured | Evidence of Running |
|---------|-----------|---------------------|
| Bridge API :8000 | Yes | run-backend.ps1, docker-compose.yml |
| Frontend :3020 | Yes | frontend/package.json, docker-compose.yml |
| Determinator :4201 | Yes | scripts/determinator-boot-agent.js |
| Redis :6379 | Yes | docker-compose.yml |
| Prometheus :9090 | Yes | docker-compose.yml + prometheus.yml |
| Grafana :3001 | Yes | docker-compose.yml + grafana-dashboard-swarm.json |
| Neo4j :7474/:7687 | Yes | docker-compose.yml |
| Cloudflare Worker | Yes | worker/wrangler.toml |
| Taurus :4202 | Yes | scripts/taurus-showcase-server.js |
| bridge-auth :3030 | Yes | bridge-auth/server.js, config |
| bridge-backend :3001 | Yes | bridge-backend/server.js, config |
| alerts.yml (Prometheus rules) | Referenced | File not found in repo |
| neo4j_connection.py | Yes (code) | Untracked (not committed yet) |
| Console sync :3022 | Config reference only | No dedicated server found |

---

## Validation Gaps & Risks

### Missing or Undocumented Environment Variables

These are referenced in code or config but have no documented defaults:

| Variable | Where Used | Risk Level |
|----------|-----------|------------|
| OPENAI_API_KEY | backend/app/routes/api.py (critical key check) | High — AI features disabled without it |
| HF_TOKEN / HUGGING_FACE_API_KEY | backend/app/routes/api.py (critical key check) | High |
| JWT_SECRET / JWT_SECRET_KEY | backend/app/routes/api.py (critical key check) | Critical — auth broken |
| CLOUDFLARE_ACCOUNT_ID | backend/app/routes/api.py, worker/wrangler.toml | High — worker deploy fails |
| ELEVENLABS_API_KEY | voice_broker service | Medium — TTS silently degrades |
| ANTHROPIC_API_KEY | api.py key check | Low — optional |
| PAYSTACK_WEBHOOK_SECRET / PAYSTACK_SECRET_KEY | payment_rails.py | Medium — webhooks accept unauthenticated in dev |
| PAYPAL_WEBHOOK_ID | payment_rails.py | Medium — webhook verification placeholder in prod |
| NEO4J_AUTH | docker-compose.yml (hardcoded: `neo4j/bridge123`) | Medium — hardcoded credential in compose |
| GF_SECURITY_ADMIN_PASSWORD | docker-compose.yml (hardcoded: `admin`) | Medium — hardcoded Grafana password |
| REDIS_URL | docker-compose.yml env (set), bridge-auth | Low — defaults to redis://redis:6379/0 |
| BRIDGE_LIVE_WALL_PATH | backend/app/routes/api.py | Low — defaults to C:/Users/supas/BridgeLiveWall (hardcoded path) |
| DETERMINATOR_NEXT_URL | scripts/determinator-boot-agent.js | Low — defaults to http://localhost:8000 |
| FRONTEND_URL | scripts/determinator-boot-agent.js | Low — defaults to http://localhost:3020 |

### Orphan Infrastructure

| Item | Issue |
|------|-------|
| `alerts.yml` | Referenced in prometheus.yml rule_files but file does not exist in repo |
| `console-sync :3022` | Listed in config ports.registry and CLAUDE.md but no server code found |
| `nextjs-app :3032` | Referenced in config but code lives in external AOE repo |
| `remote_write` in prometheus.yml | Points to localhost:9090 (self-loop) — likely placeholder |
| `neo4j_connection.py` | Code exists (untracked) but knowledge_graph.py uses in-memory store, not Neo4j driver |
| `bridge_defi/frontend/` | Has own package.json/Vite config but no backend wiring found |
| `data/twin-registry.json` | Required by /api/wiki/registry but generated only after running sync-twins-wiki.ps1 |

### Security Risks

| Risk | Location | Severity |
|------|----------|---------|
| Hardcoded Neo4j password `neo4j/bridge123` | docker-compose.yml line 68 | Medium |
| Hardcoded Grafana admin password `admin` | docker-compose.yml line 53 | Medium |
| Hardcoded fallback path `C:/Users/supas/BridgeLiveWall` | backend/app/routes/api.py line 1037 | Low — developer machine path leaked |
| Determinator RBAC is a stub | scripts/determinator-boot-agent.js line 60 | High — accepts any user/pass, no real auth |
| PayPal webhook verification is a placeholder | backend/app/services/payment_rails.py line 124 | High — webhooks not verified in production |
| CORS allows all localhost origins including regex | backend/app/main.py | Low — intentional for dev; verify prod config |
| ELEVEN_API_KEY in docker-compose.yml is blank | docker-compose.yml line 10 | Low — TTS silently disabled |
| Evolution budget not persisted | In-memory only (physics.py) | Medium — budget resets on restart |
| Revenue / treasury state not persisted | In-memory only (RevenueService) | High — all balances lost on restart |
| Replication node registry | Redis (cleared on restart without AOF) | Medium — mesh lost on restart |

### Broken / Missing Dependencies

| Item | Issue |
|------|-------|
| `backend/requirements.txt` missing `prometheus_client` | telemetry.py imports it but it is not in requirements.txt |
| `backend/requirements.txt` missing `neo4j` driver | neo4j_connection.py would need it |
| `backend/requirements-test.txt` | Referenced in CI but not found during scan |
| `tools/state/verify.cjs` | Referenced in frontend/package.json build script — not scanned |

---

## Architecture Diagrams

### Existing Diagrams / Documented

| File | Location | Type |
|------|----------|------|
| system-map.drawio.xml | docs/diagrams/ (referenced) | Draw.io — full system topology |
| BRIDGE.DRAWIO | docs/diagrams/ (referenced) | Bridge AI OS architecture |
| grafana-dashboard-swarm.json | docs/grafana-dashboard-swarm.json | Grafana swarm dashboard |
| wall.svg | wall.svg (root) | SVG wallpaper diagram |
| twin_wall.png | twin_wall.png (root) | Live wallpaper (generated) |
| wall.png | wall.png (root) | Static wallpaper |

### Referenced Docs (Architecture Coverage)

| Doc | Topic |
|-----|-------|
| docs/ARCHITECTURE.md | General architecture |
| docs/GLOBAL-TWIN-SWARM-ARCHITECTURE.md | Global swarm topology |
| docs/PLANETARY-SCALE-AGENT-TOPOLOGY.md | Planetary-scale agent layers |
| docs/SWARM-TOPOLOGY-5-LAYER.md | 5-layer swarm topology |
| docs/SELF-EXPANDING-AI-NETWORK.md | Self-expanding network design |
| docs/REPO-STATE-AND-TARGET-ARCHITECTURE.md | Repo state vs target architecture |
| docs/SYSTEM-MAP-FULL.md | Full system map |
| docs/AUDIT-SYSTEM-MAP-4201.md | System Map (4201) audit |
| docs/AUDIT-FRONTEND-BACKEND-CLOUD.md | Frontend + backend + cloud audit |
| docs/TWIN-SYSTEM-TECHNICAL-ASSESSMENT.md | Technical assessment |
| docs/DEPLOY-CHECKLIST.md | Deployment checklist |
| docs/INTEGRATION-NOTES-AOE-SUPACO.md | AOE/Supaco integration notes |
| docs/SPINE.md | SPINE architecture (Endpoint → Reducer → State → Scheduler → Expression) |
| docs/SPEECH_COMMUNICATION_DIRECTIVE.md | Speech embodiment pipeline |
| docs/SENSORS-WIFI-MOUSE-BOOT.md | Boot-time sensor docs |

### Diagrams Needed (Gaps)

| Diagram | Priority | Notes |
|---------|----------|-------|
| Service dependency graph | High | Which services depend on which — Redis, Neo4j, Prometheus, etc. |
| API endpoint map | High | All /api/* routes in one visual |
| Revenue flow diagram | High | marketplace → revenue → treasury → UBI/Treasury/Ops/Founder |
| Auth flow diagram | High | SIWE → JWT → bridge-auth → Bridge API |
| Data persistence map | High | What lives in Redis vs in-memory vs file vs Neo4j |
| Deployment topology | Medium | Local vs Docker vs Cloudflare Worker vs production |
| Twin lifecycle diagram | Medium | Twin creation → competition → leaderboard → replication |
| WebSocket channel map | Low | /ws/{channel} routing and message types |

---

## Quick Reference: SPINE Architecture

The Bridge API follows the **SPINE** pattern documented in the codebase:

```
Perception → Decision → Expression → Economic Effect → State Update → Evolution
Endpoint   → Reducer  → State      → Scheduler       → Expression
```

- **State mutations** require a sanctioned reducer (`/api/state`) + authority class
- **Evolution** requires `orchestrator` authority + evolution budget + governance vote to commit
- **Identity** fields (core_values, mission_alignment, authority_class) are immutable
- **Deterministic mode**: same inputs → same output (seed from state_version + input hash)
- **Ethical conflict**: silences output rather than producing harmful action

---

*Blueprint generated by autonomous workspace scan. All data sourced directly from files in E:\BridgeAI\BridgeLiveWall. No values guessed.*
