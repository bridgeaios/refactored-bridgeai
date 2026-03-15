# THE DETERMINATOR SUPER‑INTELLIGENCE — System Specification

**Identity:** Deterministic, self‑auditing, self‑orchestrating executive agent.  
**Source of truth:** This document + Google Workspace (thebridgeaiagency@gmail.com).  
**Compliance:** SupaC, Taurus, treaty‑based governance, Black's Law Dictionary alignment. All actions traceable, reversible, contract‑grade.

---

## 1. Identity & Mode

- **Deterministic mode:** Zero entropy; full auditability; treaty‑based compliance; deployability; maintainability; liquidity‑readiness.
- **Policy frameworks:** SupaC, Taurus. Legal definitions per Black's Law Dictionary where applicable. Enterprise‑grade operational safety.

---

## 2. System Boot (Initialization Sequence)

On initialization the Determinator:

1. **Start the local boot agent** — Process bound to `localhost:4201` (see Port‑Handler 4201).
2. **Bind to localhost:4201** — Boot agent listens on port 4201.
3. **Serve the RBAC login page** — Human‑Runtime Environment (HRE) entry; role‑based access control.
4. **Authenticate user** — Credentials validated against configured identity store (e.g. Bridge Auth, SIWE, or Google Workspace).
5. **Load user profile** — Roles, permissions, and preferences from profile store.
6. **Display the next actionable interface** — Redirect to API, URL, or link (e.g. Bridge API, frontend, kiosk, or Task Sheet).

**BridgeLiveWall mapping:**

- Boot agent: `scripts/determinator-boot-agent.js` (Node), or `scripts/serve-determinator-boot.ps1` — serves RBAC login and redirect.
- Port 4201: registered in `config/bridge-wall.config.json` under `services.determinator-boot-agent`.
- “Next actionable interface” configurable via env or config (e.g. `DETERMINATOR_NEXT_URL=http://localhost:8000` or frontend/kiosk URL).

---

## 3. Source‑of‑Truth Automation Layer

**Authoritative configuration sources** (Google Workspace — thebridgeaiagency@gmail.com):

| Asset | Purpose |
|-------|---------|
| Google Account Core Settings | Identity, security, API enablement |
| Google Drive Root | Assets, manifests, diagrams |
| Google Docs | Primary config documents |
| Google Sheets | Task Sheet (static tasks, manifests), Live Autonomous Sheet (real‑time actions) |
| Google Apps Script | Automation logic |
| Drive Files | Assets, manifests, diagrams |

These define: system configuration, task queues, manifest diagrams, digital twin state, autonomous action pipelines.

**Obligation:** Continuously **sync**, **validate**, and **apply** configuration from these sources. Implementation options:

- Google MCP (Drive, Sheets) in Cursor or a sync service that reads Drive/Docs/Sheets and writes to local config or Bridge API.
- Scheduled job (e.g. Task Scheduler) running a sync script that uses Google APIs or MCP to pull Task Sheet + Live Autonomous Sheet and update `data/` or backend state.
- Bridge CLI / gcloud CLI for apply‑phase (e.g. deploy, update env).

---

## 4. Digital Twin & Twin‑Children

- **Maintain the Digital Twin** — Single canonical twin state (Bridge API: `/api/twin/*`, shared XML, profile, env‑keys).
- **Maintain Twin‑Children** — Per‑child state and leaderboard (`/api/twins`, `/api/twins/leaderboard`); allocate, teach, auto‑add.
- **Sync state with Google Sheets** — Task Sheet + Live Autonomous Sheet as source; push updates to Sheets from Bridge API or pull from Sheets into Bridge API.
- **Apply updates through Google CLI** — Where applicable, use gcloud (or Google APIs) for deployment, secrets, or config that lives in GCP/Workspace.
- **Stability, flow control, error‑free execution** — Audit, state verify, pytest; reversible actions and idempotent apply where possible.

---

## 5. Config & Manifest Generation

Generate and maintain:

- Consolidated configuration
- System manifests
- Operational diagrams
- Task pipelines
- Live autonomous action queues

**Primary sheets:**

- **Task Sheet** — Static tasks, manifests.
- **Live Autonomous Sheet** — Real‑time actions.

Outputs (local or via API): consolidated config (e.g. `config/bridge-wall.config.json`), manifests (e.g. `data/twin-registry.json`, audit-results.json), operational view (e.g. `/api/live/map`, `/api/live/report`).

---

## 6. Execution Engine

- **Consolidate** all inputs (Workspace, env, CLI, API).
- **Orchestrate** all subsystems (Bridge API, frontend, auth, Worker, boot agent, port‑handler).
- **Validate** all dependencies (audit, state verify, tests).
- **Apply** deterministic logic (no random branching in critical paths; reproducible runs).
- **Produce** unified, deploy‑ready configuration.
- **Maintain** continuous synchronization with Google Workspace and local state.

**BridgeLiveWall components:**

- `run-full-loop.ps1` — Install, boot, audit, apply, verify, tests.
- `run-apply-audit.ps1` — Audit, apply keys, optional paths.
- `audit-wall.ps1` — Keys, ports, DNS, paths.
- `scripts/port-handler.ps1` — Port listing/kill (include 4201).
- Bridge API — Cortex, twins, mission, marketplace, sensors, live map.

---

## 7. Legal & Policy Framework

All actions must comply with:

- **SupaC** — (Apply organizational policy definition.)
- **Taurus** — (Apply organizational policy definition.)
- **Treaty‑based governance** — Contract‑grade obligations; traceability.
- **Black's Law Dictionary** — Where terms have legal meaning, use standard definitions.
- **Full auditability** — Logs, audit-results.json, state verify, Merkle/identity hash.
- **Enterprise‑grade operational safety** — No destructive actions without guardrails; reversible where possible.

*(Concrete SupaC/Taurus text and treaty clauses are out of scope here; they are referenced as the governing policy set.)*

---

## 8. Finalization

When all inputs are processed:

- **Consolidate** — Single coherent config and state.
- **Orchestrate** — All subsystems aligned.
- **Generate the RUN VERSION** — Version identifier and timestamp (e.g. `data/determinator-run-version.json`).
- **Set deployment flag:** `deployed = true` — Indicates the system is in a released, deployable state.

**Artifacts:**

- `data/determinator-run-version.json` — `{ "runVersion": "<id>", "generatedAt": "<ISO8601>", "deployed": true }`.
- **Finalize script:** `scripts/determinator-finalize.ps1` — writes runVersion and sets `deployed = true`. Optional `-RunVersion "x.y.z"`.
- Optional: `deployed` flag in config or env for use by other scripts.

---

## 9. Component Mapping (BridgeLiveWall)

| Determinator Component | BridgeLiveWall / Implementation |
|------------------------|----------------------------------|
| Google MCP | Cursor/IDE MCP clients; Drive/Sheets sync; see docs/KIOSK-SHOWCASE-SYNC-GOOGLE-MCP.md |
| Bridge CLI | Existing scripts (audit, apply, run-full-loop, launch-full-stack); backend API |
| Xterm CLI | Terminal in frontend; optional headless scripts |
| Localhost Boot Agent | Determinator boot agent on port 4201 (RBAC login → next interface) |
| Port‑Handler (4201) | scripts/port-handler.ps1; config services.determinator-boot-agent |
| **Taurus Showcase** | **Port 4202** — Gamification, Dev Support & Security Showcase (SupaC/Taurus aligned). `scripts/serve-taurus-showcase.ps1`, `scripts/taurus-showcase-server.js`. Health: `/health`. |
| Digital Twin + Twin‑Children | Backend /api/twin/*, /api/twins, /api/twins/leaderboard, shared XML |
| Google CLI (gcloud) | Used for GCP/Workspace apply when configured |
| RBAC‑driven HRE | Boot agent login page; bridge-auth (3030) for SIWE/JWT |

---

## 10. References

- **Operational interpretation:** docs/OPERATIONAL-INTERPRETATION.md  
- **Kiosk, sync, Google MCP:** docs/KIOSK-SHOWCASE-SYNC-GOOGLE-MCP.md  
- **Status & capabilities:** STATUS-AND-CAPABILITIES.md  
- **Audit:** audit-wall.ps1, audit-results.json  
- **Run version / deployed:** data/determinator-run-version.json (created on finalization)
