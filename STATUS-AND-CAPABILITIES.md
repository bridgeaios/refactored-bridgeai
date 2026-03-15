# Bridge Live Wall — Full Status Update & Capabilities

**Generated:** 2026-03-15

**Operational interpretation (system integrity, topology, cortex state, twin mesh):** see **docs/OPERATIONAL-INTERPRETATION.md**.  
**Determinator (boot agent 4201, RBAC HRE, run version, deployed flag):** see **docs/DETERMINATOR-SYSTEM-SPEC.md**.  
**Full audit (3020, dashboard, digital twins, APIs, sync, GET/POST) and full run (install → build → debug → deploy):** see **docs/FULL-AUDIT-3020-DASHBOARD-TWINS.md** and **run-full-install-build-deploy.ps1** (goal = task = goal in data/goals-tasks.json).  
**Rebase / branch / commit checklist:** see **docs/REBASE-BRANCH-COMMIT-CHECKLIST.md**. **Changes for review (added/changed list):** see **docs/CHANGES-FOR-REVIEW.md**.

---

## 1. Full status update

### Audit & health

| Item | Status |
|------|--------|
| **Audit (audit-wall.ps1)** | PASS — 0 critical, 23 OK, 8 recommendations |
| **Backend API tests (pytest)** | 27/27 passed |
| **State verify** | OK (audit/twin_wall excluded from Merkle; approve once if root mismatch) |

### Services (ports)

| Service | Port | Status (per last audit) |
|---------|------|-------------------------|
| bridge-backend | 3001 | Listening |
| Bridge API (Docker / run-backend) | 8000 | Listening |
| Redis | 6379 | Listening |
| Installer | 7777 | Listening |
| Vite (frontend dev) | 5173 | Listening |
| Dashboard | 3000 | Not running |
| frontend | 3020 | Not running |
| bridge-auth | 3030 | Not running |
| Determinator Boot Agent | 4201 | Not running |
| Taurus Showcase | 4202 | Not running |

### Deployment & DNS

| Item | Status |
|------|--------|
| **Cloudflare Worker** | Deployed — **api.bridge-ai-os.tech** (custom domain) |
| **Worker URL** | https://api.bridge-ai-os.tech |
| **R2 bucket** | bridge-live-wall (bindable in wrangler; set R2_BUCKET_NAME in .env) |

### Boot & automation

| Item | Description |
|------|-------------|
| **install-startup.ps1** | Adds Bridge API (run-backend.ps1) to Windows Startup |
| **install-sensors-boot.ps1** | Adds WiFi RF + mouse tracker scripts to Startup (run after backend at logon) |
| **run-full-loop.ps1** | Install → boot → audit → apply → verify → pytest; use `-ApproveStateOnce` if needed |
| **run-apply-audit.ps1** | Audit → apply (inject from AOE + apply-keys + optional paths). No install/boot/tests. Use for quick “run apply audit”. |
| **launch-full-stack.ps1** | One-shot: start API, bridge-backend, bridge-auth, frontend (full stack). Set BRIDGE_ROOT if needed. |
| **run-full-install-build-deploy.ps1** | Full run: install → build → debug → deploy; log in logs/; goals in data/goals-tasks.json. -SkipDeploy / -ApproveStateOnce. |
| **run-debug-loop-learn-install-deploy-display.ps1** | Debug → Loop (audit/fix) → Learn (goals) → Install → Deploy → Display (URLs + open frontend). -SkipDeploy / -SkipDisplay / -ApproveStateOnce. |

### Keys & config (audit OK)

- OpenAI, Hugging Face, Cloudflare, JWT, Turnstile, ElevenLabs, Anthropic, SMTP, PayPal, Discord Bot, AWS credentials, AWS CLI.
- Config: `config/bridge-wall.config.json` found.
- Paths: E: AOE, E: BridgeLiveWall, E: AOE .env, C: AWS credentials.

### Optional / recommendations (non-blocking)

- Start bridge-auth (3030), frontend (3020), dashboard (3000) if needed: `.\scripts\start-recommended-services.ps1`
- DNS: api.bridge-ai-os.tech — add record in Cloudflare if not auto-created
- R2: set R2_BUCKET_NAME in .env; create bucket per docs/CLOUDFLARE-DNS-R2.md
- Optional D: paths: `.\scripts\ensure-optional-paths.ps1`

---

## 2. Full list of capabilities

### A. Cortex capabilities (backend — twin/orchestrator flags)

Controlled by `CAPABILITIES` in `backend/app/cortex.py`; overridable via `BRIDGE_CAP_*` env (e.g. `BRIDGE_CAP_TRADE=0`). Lock with `BRIDGE_CAP_LOCK=1` to freeze at boot.

| Capability | Default | Description |
|------------|--------|-------------|
| **perception** | On | Twin perception / input handling |
| **speech** | On | Speech reasoning and embodiment |
| **trade** | On | BossBots / economic trade |
| **ubi** | On | UBI claim and flow |
| **simulate** | On | Twin simulation |
| **evolution** | On | Twin evolution |
| **marketplace** | On | Marketplace tasks, pledge, accept, complete |
| **state_mutation** | On | State mutation via reducers |

### B. Optional features (config — optional.features)

From `config/bridge-wall.config.json`. Enable/disable via config or env where supported.

| Feature | Default | Description |
|---------|--------|-------------|
| **siwe** | On | Sign-In with Ethereum |
| **jwt** | On | Short-lived JWT + refresh |
| **refreshTokens** | On | Refresh token rotation |
| **onChainRole** | Off | On-chain role check |
| **websocketEvents** | On | WebSocket push for contract events |
| **sqliteNonce** | On | SQLite replay protection / nonce |
| **redisSessions** | On | Redis-backed sessions (bridge-auth) |
| **turnstile** | Off | Cloudflare Turnstile |
| **elevenLabs** | Off | ElevenLabs TTS |
| **openai** | On | OpenAI APIs |
| **anthropic** | Off | Anthropic APIs |
| **huggingFace** | On | Hugging Face |
| **cloudflareR2** | Off | Cloudflare R2 storage |
| **smtp** | Off | SMTP |
| **paypal** | Off | PayPal |
| **discordBot** | Off | Discord bot |
| **awsCli** | Off | AWS CLI usage |

### C. Config capabilities (config — capabilities)

Documented in config; describe auth/security surface.

| Capability | Description |
|------------|-------------|
| **siwe** | Sign-In with Ethereum |
| **jwt** | Short-lived JWT + refresh rotation |
| **sqliteNonce** | SQLite replay protection / nonce |
| **onChainRole** | On-chain role check |
| **websocketEvents** | WebSocket push for contract events |
| **redisSessions** | Redis-backed sessions (bridge-auth) |
| **cors** | Configurable CORS allowed domains |
| **helmet** | Security headers (bridge-auth) |

### D. Bridge API (Python) — endpoints

Base: `http://localhost:8000` or `https://api.bridge-ai-os.tech`.

**Health & root**

- `GET /` — Root + identity hash
- `GET /health` — Health
- `GET /health/extended` — Extended health

**Mission & state**

- `GET /mission/board` — Mission board
- `POST /skills` — Add skill
- `GET /state/snapshot` — State snapshot (if exposed)
- State mutation (reducer-only) as implemented

**Twin**

- `GET /twin/shared-xml` — Shared XML
- `POST /twin/shared-xml` — Update shared XML
- `GET /twin/profile` — Twin profile
- `GET /twin/env-keys` — Env keys
- `POST /twin/decide` — Twin decide
- `POST /twin/simulate` — Twin simulate
- `POST /twin/evolve` — Twin evolve

**Emotion & UBI**

- `POST /emotion/compute` — Emotion compute
- `POST /ubi/claim` — UBI claim

**Speech**

- `POST /speech/reason` — Speech reasoning
- `POST /speech/embody` — Speech embody
- `POST /speech/embody/speak` — Speak
- `GET /speech/embodiment/skill` — Skill definition
- `POST /speech/embodiment/memory/clear` — Clear memory
- `GET /speech/embodiment/memory` — Memory

**Training & ESIM**

- `POST /train/start` — Start training
- `GET /train/status` — Training status
- `GET /esim/status` — ESIM status

**Marketplace**

- `GET /marketplace/tasks` — List tasks
- `POST /marketplace/task` — Create task
- `POST /marketplace/pledge` — Pledge
- `POST /marketplace/accept` — Accept
- `POST /marketplace/complete` — Complete

**Live & orchestration**

- `GET /live/map` — Full map (pboots, runbs, twins, capabilities, telemetry, services, **sensors**)
- `GET /live/report` — Live report (map + report_at)
- `GET /orchestrate/directives` — List directives (scripts to run)

**Sensors (boot scripts)**

- `POST /api/sensors/wifi` — Ingest WiFi RF sample
- `GET /api/sensors/wifi` — Latest WiFi sample
- `POST /api/sensors/mouse` — Ingest mouse sample
- `GET /api/sensors/mouse` — Latest mouse sample

**Wiki & registry**

- `GET /wiki/registry` — Twin registry (sync-twins-wiki)

**Twins competition**

- `GET /twins` — List twins
- `GET /twins/leaderboard` — Leaderboard
- `POST /twins/auto-add` — Auto-add task
- `POST /twins/allocate` — Allocate task
- `POST /twins/teach` — Teach skill

**SDG & revenue**

- `GET /sdg/metrics` — SDG metrics
- `GET /revenue/status` — Revenue status

**BossBots**

- `POST /bossbots/trade` — Execute trade
- `GET /bossbots/signals` — Signals

**System comprehension**

- `GET /system/comprehension` — System comprehension
- `GET /system/comprehension/explain` — Explain
- `GET /system/comprehension/operational-model` — Operational model
- `GET /system/comprehension/role-awareness` — Role awareness
- `POST /system/comprehension/check-alignment` — Check alignment
- `POST /system/comprehension/evolve` — Evolve
- `GET /system/comprehension/skill` — Skill

**Audit & TTS**

- `GET /audit/drift` — Audit drift
- `GET /tts/available` — TTS available
- `POST /tts` — TTS

**Founder**

- `GET /founder-todo` — Founder todo list
- `PATCH /founder-todo/{obj_id}/complete` — Mark complete

### E. Cloudflare Worker (api.bridge-ai-os.tech)

- Health check
- Optional R2 binding (bucket: bridge-live-wall)
- Proxy/forwarding as configured in worker

### F. Boot-time sensors

| Sensor | Script | Endpoint | Description |
|--------|--------|----------|-------------|
| **WiFi RF** | scripts/wifi-rf-boot.ps1 | POST/GET /api/sensors/wifi | SSID, signal %, state (netsh) |
| **Mouse tracker** | scripts/mouse-tracker-boot.ps1 | POST/GET /api/sensors/mouse | Cursor x, y (Forms.Cursor) |

Install at logon: `.\install-sensors-boot.ps1` (after backend is in Startup).

### G. Modules (config — modules)

| Module | Description |
|--------|-------------|
| bridge-backend | Sovereign entry — SIWE, nonce, JWT, WebSocket |
| bridge-auth | Identity & authority — SIWE, session, refresh, WebSocket |
| frontend | Vite, Babylon, viem |
| redis | Session/store for bridge-auth |
| audit | audit-wall.ps1 — keys, ports, DNS, drives |

### H. Scripts & automation

| Script | Purpose |
|--------|--------|
| install-all.ps1 | Install Python deps, bridge-backend npm, optional frontend |
| install-startup.ps1 | Add Bridge API to Windows Startup |
| install-sensors-boot.ps1 | Add WiFi RF + mouse tracker to Startup |
| run-backend.ps1 | Start Bridge API (port 8000, reload) |
| run-full-loop.ps1 | Install → boot → audit → apply → verify → pytest |
| audit-wall.ps1 | Full audit (keys, ports, DNS, paths) |
| scripts/setup-r2-and-deploy.ps1 | Create R2 bucket, uncomment wrangler R2, deploy worker, set R2_BUCKET_NAME in .env |
| scripts/start-recommended-services.ps1 | Start API, bridge-backend, bridge-auth, frontend if not listening |
| scripts/port-handler.ps1 | List/kill by port |
| scripts/sync-twins-wiki.ps1 | Sync twins + wiki registry |
| scripts/wifi-rf-boot.ps1 | WiFi sensor loop → POST /api/sensors/wifi |
| scripts/mouse-tracker-boot.ps1 | Mouse sensor loop → POST /api/sensors/mouse |
| launch-full-stack.ps1 | One-shot full stack (API + backend + auth + frontend) |
| run-apply-audit.ps1 | Audit then apply keys/paths (optional fix loop) |
| run-full-install-build-deploy.ps1 | Install, build, debug, deploy + full log + goal=task |
| run-debug-loop-learn-install-deploy-display.ps1 | Debug, loop, learn, install, deploy, display |
| scripts/serve-determinator-boot.ps1 | Start Determinator Boot Agent on 4201 (RBAC login → next URL) |
| scripts/determinator-finalize.ps1 | Set RUN VERSION and deployed=true (Determinator finalization) |
| scripts/serve-taurus-showcase.ps1 | Taurus — Gamification, Dev Support & Security Showcase (port 4202) |
| scripts/google-storage-sync.ps1 | One-shot: Google Drive / Sheet / local Excel → data/storage-sync.json (viewable at :4202) |
| scripts/google-storage-sync.sh | Same (bash): set GOOGLE_DRIVE_FILE_ID, GOOGLE_SHEET_ID, or LOCAL_EXCEL_PATH |

**Kiosk, showcase, sync & Google MCP:** See **docs/KIOSK-SHOWCASE-SYNC-GOOGLE-MCP.md** for run-apply-audit usage, kiosk mode, showcase content (all included), sync with other projects, and Google MCP (Drive/Calendar) integration.

---

**Summary:** Audit 0 critical; 27/27 tests pass; Bridge API + Worker + Redis + backend + installer running where expected. Cortex, config, API, Worker, sensors, and scripts form the full capabilities set above.
