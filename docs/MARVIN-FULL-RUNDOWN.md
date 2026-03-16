# Full Rundown for Marvin — Bridge AI OS / BridgeLiveWall

**Purpose:** Single reference for updating Marvin (or any agent) with all aspects, capabilities, run/deploy behavior, and current state.  
**Generated:** 2026-03-15

---

## 1. What the system is

- **Name:** Bridge AI OS (repo: BridgeLiveWall).
- **Role:** Decentralized AI orchestration platform — “AI Operating System Kernel” with memory, wallet auth, API discovery, agent runtime scaffolding. No on-box LLM yet (no GGUF/CUDA inference); control plane and economy are in place.
- **Stack:** Python (FastAPI) backend, Node (bridge-backend, bridge-auth), Vite/Babylon frontend, Redis, SQLite (SIWE nonce), Cloudflare Worker + R2.
- **Deployed edge:** **https://api.bridge-ai-os.tech** (Worker; R2 bucket: bridge-live-wall).

---

## 2. Services and ports

| Service | Port | Typical status |
|--------|------|----------------|
| Bridge API | 8000 | Listening (main backend) |
| bridge-backend | 3001 | Listening |
| Redis | 6379 | Listening |
| Installer | 7777 | Listening |
| Vite (frontend dev) | 5173 | Listening |
| Dashboard | 3000 | Placeholder; not running |
| Frontend (prod) | 3020 | Not running (start separately) |
| bridge-auth | 3030 | Not running |
| Determinator Boot Agent | 4201 | Not running |
| Taurus Showcase | 4202 | Not running |

---

## 3. Capabilities (cortex + config)

**Cortex (backend/app/cortex.py; override with BRIDGE_CAP_*):**

- perception, speech, trade, ubi, simulate, evolution, marketplace, state_mutation (all On by default). Lock with BRIDGE_CAP_LOCK=1.

**Config (config/bridge-wall.config.json):**

- siwe, jwt, refreshTokens, onChainRole, websocketEvents, sqliteNonce, redisSessions, turnstile, elevenLabs, openai, anthropic, huggingFace, cloudflareR2, smtp, paypal, discordBot, awsCli.

**Data:**

- Redis: primary (memory_store, cortex, contract_listener, auth sessions).
- SQLite: SIWE nonce only.
- File fallback: MemoryStore when Redis unavailable.

---

## 4. API surface (Bridge API, base /api)

**Health & root:** GET /, /api/health, /api/health/extended  
**Mission & state:** GET /api/mission/board, POST /api/skills, GET /api/state/snapshot, POST /api/state (reducers)  
**Twin:** GET/POST /api/twin/shared-xml, GET /api/twin/profile, /api/twin/env-keys, POST /api/twin/decide, simulate, evolve  
**Emotion & UBI:** POST /api/emotion/compute, POST /api/ubi/claim  
**Speech:** POST /api/speech/reason, embody, embody/speak; GET/POST speech/embodiment/skill, memory, memory/clear  
**Training & ESIM:** POST /api/train/start, GET /api/train/status, GET /api/esim/status  
**Marketplace:** GET /api/marketplace/tasks, POST task, pledge, accept, complete  
**Live & orchestration:** GET /api/live/map, /api/live/report, GET /api/orchestrate/directives  
**Sensors:** POST/GET /api/sensors/wifi, POST/GET /api/sensors/mouse  
**Wiki:** GET /api/wiki/registry  
**Twins competition:** GET /api/twins, /api/twins/leaderboard, POST /api/twins/auto-add, allocate, teach  
**Replication & node discovery:** GET /api/replication/status, GET /api/replication/nodes, POST /api/replication/register  
**SDG & revenue:** GET /api/sdg/metrics, /api/revenue/status  
**BossBots:** POST /api/bossbots/trade, GET /api/bossbots/signals  
**System comprehension:** GET /api/system/comprehension, explain, operational-model, role-awareness, skill; POST check-alignment, evolve  
**Audit & TTS:** GET /api/audit/drift, GET /api/tts/available, POST /api/tts  
**Founder:** GET /api/founder-todo, PATCH /api/founder-todo/{id}/complete  

All routes live in backend/app/routes/api.py; OpenAPI spec: openapi.json.

---

## 5. Replication engine and swarm

- **Replication engine:** backend/app/services/replication.py. Rules: (1) task demand > agent capacity → auto_add + optional register_twin; (2) twin performance > threshold → spawn variant. Status in memory (replication:status). Loop runs every BRIDGE_REPLICATION_SEC (default 90).
- **Node discovery:** POST /api/replication/register (node_id, url, capabilities); GET /api/replication/nodes. Stored in memory (replication:nodes).
- **Docs (apply before deploy / scale):** SWARM-SCALING-RISKS-AND-FIXES.md (28 risks + global task bus), SWARM-TOPOLOGY-5-LAYER.md (1k→1M agents), SWARM-SCALE-UNLIMITED-5-TRICKS.md (fractal, gossip, event streams, capability routing, economic regulation), PLANETARY-SCALE-AGENT-TOPOLOGY.md (planetary mesh + 10 capabilities + 7-plane stack), DEPLOY-CHECKLIST.md.

---

## 6. Scripts and automation

| Script | Purpose |
|--------|--------|
| install-all.ps1 | Python deps, bridge-backend npm, frontend npm |
| audit-wall.ps1 | Audit keys, ports, DNS, paths → audit-results.json |
| apply-keys.ps1 | .env from .env.example if missing |
| run-backend.ps1 | Start Bridge API (8000, reload) |
| run-full-install-build-deploy.ps1 | Install → build → audit → debug (state verify + pytest) → deploy (wrangler) |
| run-full-install-build-deploy.ps1 -SkipDeploy | Same without Worker deploy |
| run-full-install-build-deploy.ps1 -ApproveStateOnce | Same; on state mismatch, approve new root once (then state verify passes) |
| run-apply-audit.ps1 | Audit then apply keys/paths |
| run-full-loop.ps1 | Install → boot → audit → apply → verify → pytest |
| launch-full-stack.ps1 | One-shot: API + bridge-backend + bridge-auth + frontend |
| scripts/sync-twins-wiki.ps1 | Sync twins + wiki → data/twin-registry.json, docs/WIKI-VERSIONS.md, docs/twin-wiki.html |
| scripts/import-drawio-from-encoded.ps1 | Decode docs/diagrams/encoded_diagram.txt → digital-ecosystem-evolution.drawio.xml |
| scripts/setup-r2-and-deploy.ps1 | R2 bucket + wrangler deploy + R2_BUCKET_NAME in .env |
| scripts/wifi-rf-boot.ps1, scripts/mouse-tracker-boot.ps1 | Sensors → POST /api/sensors/wifi, /api/sensors/mouse |

**Automation (backend):** AutomationLoops in backend/app/services/automation.py — auto_add, auto_allocate, auto_complete, auto_dex, sync_board, replication. Started in main.py lifespan.

---

## 7. State verify (Merkle) and full run

- **Verifier:** node tools/state/verify.cjs. Build (frontend) runs `node tools/state/verify.cjs && vite build`; full run also runs state verify before pytest.
- **Excluded from Merkle:** .git, .bridge-state, .cursor, node_modules, dist, build, coverage, __pycache__, .pytest_cache, .venv/venv, **logs** (added so pipeline log writes don’t change root), plus files: .DS_Store, Thumbs.db, audit-results.json, twin_wall.png.
- **When root mismatches:** Build and state verify fail until approval. Approve once with:  
  `node tools/state/verify.cjs --approve`  
  or run full script with:  
  `.\run-full-install-build-deploy.ps1 -ApproveStateOnce`
- **Manifest:** .bridge-state/manifest.json; roots log: .bridge-state/roots.ndjson.

---

## 8. Full run pipeline (goal = task = goal)

1. **Install** — install-all.ps1  
2. **Build** — frontend: node tools/state/verify.cjs && vite build (state must match or be approved)  
3. **Audit** — audit-wall.ps1; if critical > 0, apply-keys.ps1 and re-audit  
4. **Debug** — state verify (Node) + pytest (Python, tests/test_api.py)  
5. **Deploy** — worker: `npx wrangler deploy` in worker/ (unless -SkipDeploy)  

**Log:** logs/full-install-build-deploy.log  
**Goals/tasks:** data/goals-tasks.json  

**Current test count:** 31 (including replication status, replication nodes, replication register).

---

## 9. Diagrams and docs

- **Draw.io:** docs/diagrams/ — BRIDGE.DRAWIO, digital-ecosystem-evolution.drawio.xml. Import from encoded paste: put content in docs/diagrams/encoded_diagram.txt, run scripts/import-drawio-from-encoded.ps1.
- **Google Drive diagram:** https://drive.google.com/file/d/1aebwruTyIYZYe8fkOn8R9njOtcL82z0c/view?usp=sharing (Digital Ecosystem Evolution).
- **Key docs:** STATUS-AND-CAPABILITIES.md, FULL-AUDIT-3020-DASHBOARD-TWINS.md, OPERATIONAL-INTERPRETATION.md, DETERMINATOR-SYSTEM-SPEC.md, REPO-STATE-AND-TARGET-ARCHITECTURE.md, SELF-EXPANDING-AI-NETWORK.md, GLOBAL-TWIN-SWARM-ARCHITECTURE.md, DEPLOY-CHECKLIST.md, SWARM-*.md, PLANETARY-SCALE-AGENT-TOPOLOGY.md, PROMPT-SYSTEM-DIAGRAM.md, CONTRACTS.md, SPINE.md, ARCHITECTURE.md.

---

## 10. Terminal issue and fix (state verify failing on full run)

- **Symptom:** run-full-install-build-deploy.ps1 writes to logs/full-install-build-deploy.log during the run, so the Merkle tree changes between build step and debug step, and state verify reports “State mutation detected (root mismatch)” and Build result: FAIL, State verify: FAIL.
- **Fix applied:** **logs** added to DEFAULT_EXCLUDE_DIR_NAMES in tools/state/verify.cjs so that the logs/ directory is excluded from the Merkle hash. Subsequent full runs should not flip the root just from appending to the pipeline log.
- **If new files or code change the root:** Run `node tools/state/verify.cjs --approve` once, or use `.\run-full-install-build-deploy.ps1 -ApproveStateOnce`.

---

## 11. Summary for Marvin

- **System:** Bridge AI OS — orchestration kernel + Redis + API + Worker + replication + economy; no on-box LLM yet.
- **APIs:** All under /api; 31 tests in tests/test_api.py; OpenAPI in openapi.json.
- **Replication:** ReplicationEngine + /api/replication/status, /api/replication/nodes, /api/replication/register; automation loop every 90s.
- **Run/deploy:** run-full-install-build-deploy.ps1 (install → build → audit → debug → deploy); state verify uses Merkle; **logs/** excluded so pipeline log no longer causes root mismatch.
- **Deploy:** Worker at https://api.bridge-ai-os.tech; R2 bridge-live-wall.
- **Docs:** STATUS-AND-CAPABILITIES.md + docs/*.md (swarm, planetary, deploy checklist, audit, diagrams). Use this rundown to keep Marvin’s context aligned with the repo.
