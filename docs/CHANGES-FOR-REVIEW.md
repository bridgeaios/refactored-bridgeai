# Changes for Review (pre-rebase / commit)

**Scope:** All added and modified files from this session. Manifest tracks **223 files**; below are the ones that were **added** or **changed** for review.

---

## Added files (28)

| File | Purpose |
|------|--------|
| **STATUS-AND-CAPABILITIES.md** | Full status + capabilities list; references all docs and scripts. |
| **data/determinator-run-version.json** | RUN VERSION + `deployed` flag for Determinator finalization. |
| **data/goals-tasks.json** | Goal = task = goal; lastRun updated by pipeline. |
| **data/storage-sync.json** | Placeholder for Google Drive/Sheet/local Excel sync; viewable at :4202. |
| **docs/DETERMINATOR-SYSTEM-SPEC.md** | Determinator spec: boot 4201, RBAC, Google Workspace, twin, run version. |
| **docs/FRONTEND-AUDIT-UX-UI.md** | Frontend UX/UI audit (3020, a11y, sensors, twin panel). |
| **docs/FULL-AUDIT-3020-DASHBOARD-TWINS.md** | Audit: 3020, dashboard, digital twins, APIs, sync, GET/POST, goal=task. |
| **docs/KIOSK-SHOWCASE-SYNC-GOOGLE-MCP.md** | Kiosk, showcase, sync, Google MCP, one-shot storage sync. |
| **docs/OPERATIONAL-INTERPRETATION.md** | Operational interpretation (kernel, topology, Worker, sensors). |
| **docs/SENSORS-WIFI-MOUSE-BOOT.md** | WiFi RF + mouse tracker from boot; install-sensors-boot.ps1. |
| **docs/REBASE-BRANCH-COMMIT-CHECKLIST.md** | Pre-rebase/commit: pipeline, state approve, quick checks. |
| **docs/CHANGES-FOR-REVIEW.md** | This file — change list for review. |
| **install-sensors-boot.ps1** | Add WiFi RF + mouse tracker to Windows Startup. |
| **launch-full-stack.ps1** | One-shot: API, backend, auth, frontend; path checks, BRIDGE_ROOT. |
| **run-apply-audit.ps1** | Audit → apply (inject + apply-keys + optional paths). |
| **run-debug-loop-learn-install-deploy-display.ps1** | Debug → Loop → Learn → Install → Deploy → Display. |
| **run-full-install-build-deploy.ps1** | Full run: install → build → debug → deploy; log + goals. |
| **scripts/determinator-boot-agent.js** | Boot agent on 4201: RBAC login, redirect to next URL. |
| **scripts/determinator-finalize.ps1** | Set RUN VERSION and deployed=true. |
| **scripts/google-storage-sync.ps1** | One-shot: Drive/Sheet/local Excel → storage-sync.json (PowerShell). |
| **scripts/google-storage-sync.sh** | Same (bash). |
| **scripts/mouse-tracker-boot.ps1** | Mouse position loop → POST /api/sensors/mouse. |
| **scripts/read-excel-to-json.py** | Read .xlsx first sheet → JSON for storage-sync. |
| **scripts/serve-determinator-boot.ps1** | Start Determinator boot agent on 4201. |
| **scripts/serve-taurus-showcase.ps1** | Start Taurus showcase on 4202. |
| **scripts/taurus-showcase-server.js** | Taurus server: gamification, dev support, security, /api/storage-sync. |
| **scripts/wifi-rf-boot.ps1** | WiFi RF loop → POST /api/sensors/wifi. |
| **worker/package-lock.json** | Worker npm lockfile (if added by install). |

---

## Changed files (7)

| File | Change summary |
|------|----------------|
| **.env** | Local env (may include R2 or other keys); do not commit secrets. |
| **backend/app/cortex.py** | Sensor storage: set/get sensor wifi + mouse; SENSOR_* keys. |
| **backend/app/routes/api.py** | POST/GET /api/sensors/wifi, /api/sensors/mouse; sensors in live map; twin panel + imports. |
| **config/bridge-wall.config.json** | Ports 4201, 4202; services: determinator-boot-agent, taurus-showcase; sensors section; twinsSync endpoints. |
| **frontend/index.html** | Added `#twinPanel` to side-panel. |
| **frontend/public/index.html** | Same: `#twinPanel` in side-panel. |
| **worker/wrangler.toml** | R2 uncomment/deploy config (if modified by setup-r2-and-deploy). |

---

## Review checklist

- [ ] **.env** — Confirm no secrets committed; use .env.example for structure only.
- [ ] **Backend (cortex, api)** — Sensor endpoints and live map `sensors` are additive; no breaking changes.
- [ ] **Config** — New ports 4201, 4202 and services; sensors and endpoints additive.
- [ ] **Frontend** — Only added `#twinPanel` container; no behavior change except twin panel now mounts.
- [ ] **Docs** — All new or updated; no removal of existing behavior.
- [ ] **Scripts** — New scripts; existing ones (audit, apply, run-full-loop) unchanged except STATUS references.

---

## State and tests

- **State verify:** Run `node tools/state/verify.cjs`; if mutation, run `node tools/state/verify.cjs --approve` once.
- **Audit:** `.\audit-wall.ps1` → expect 0 critical in audit-results.json.
- **Tests:** `pytest tests/` → expect 27 passed.

After review, you’re ready for rebase / branch / commit per **docs/REBASE-BRANCH-COMMIT-CHECKLIST.md**.
