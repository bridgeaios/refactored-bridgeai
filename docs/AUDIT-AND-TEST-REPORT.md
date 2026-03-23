# Full Audit and Test Report

**Generated:** 2026-03-15

---

## 1. Audit (audit-wall.ps1)

**Result:** **PASS** (0 critical)

| Metric | Value |
|--------|--------|
| OK | 23 |
| Critical | 0 |
| Recommendations | 8 |

### OK (23 items)

- **Keys:** OpenAI, Hugging Face, Hugging Face (alt), Cloudflare Account, JWT Secret, JWT Secret Key, Cloudflare Turnstile, ElevenLabs, Anthropic, SMTP, PayPal, Discord Bot
- **AWS:** credentials file exists, AWS CLI installed
- **Ports listening:** bridge-backend (3001), Installer (7777), Bridge API (Docker) (8000), Redis (6379)
- **Paths:** E: AOE exists, E: BridgeLiveWall exists, E: AOE .env exists, C: AWS credentials exists
- **Config:** config\bridge-wall.config.json found

### Recommendations (8, non-blocking)

- bridge-auth not running (port 3030)
- frontend not running (port 3020)
- Dashboard not running (port 3000)
- Frontend (Docker) not running (port 3000)
- DNS: api.bridge-ai-os.tech - add record in Cloudflare
- Cloudflare: set R2_BUCKET_NAME for storage
- Optional: D: BridgeLiveWall (optional) not found
- Optional: D: data (optional) not found

### Applied suggestions (implemented)

| Recommendation | Implementation |
|----------------|----------------|
| **DNS** api.bridge-ai-os.tech | **docs/CLOUDFLARE-DNS-R2.md** — steps to add A/CNAME record in Cloudflare. |
| **R2_BUCKET_NAME** | **.env.example**, **KEYS-REQUIRED.md**, **audit**, **backend** — key added; set in .env and create bucket per **docs/CLOUDFLARE-DNS-R2.md**. |
| **Optional D: paths** | **scripts/ensure-optional-paths.ps1** — creates D:\BridgeAI\BridgeLiveWall and D:\BridgeAI\data if D: exists. Run: `.\scripts\ensure-optional-paths.ps1` |
| **bridge-auth / frontend / backend not running** | **scripts/start-recommended-services.ps1** — starts Bridge API (8000), bridge-backend (3001), bridge-auth (3030), frontend (3020) in minimized windows if not listening. Run: `.\scripts\start-recommended-services.ps1` |

---

## 2. Backend API tests (pytest tests/test_api.py)

**Result:** **27 passed**, 1 warning

- **Command:** `$env:PYTHONPATH = "e:\BridgeAI\BridgeLiveWall\backend"; python -m pytest tests/test_api.py -v`
- **Warning:** `PendingDeprecationWarning` for `multipart` (Starlette) — cosmetic only.

### Tests passed

- test_root, test_health, test_mission_board
- test_state_mutation_ok, test_state_mutation_reducer_required, test_state_mutation_unsanctioned_reducer
- test_add_skill, test_add_skill_validation
- test_emotion_compute, test_ubi_claim, test_ubi_claim_no_address
- test_marketplace_create_and_get, test_marketplace_accept, test_marketplace_accept_missing_fields
- test_tts_text_required, test_train_status, test_sdg_metrics, test_revenue_status
- test_audit_drift, test_twin_evolve_requires_orchestrator, test_telemetry_includes_evolution_budget
- test_state_snapshot, test_health_extended, test_root_includes_identity_hash
- test_twin_decide_includes_deterministic_seed, test_telemetry_includes_degradation_and_drift
- test_physics_cohesion_capability_off

---

## 3. Port status (scripts/port-handler.ps1 list)

| Service | Port | Listening |
|---------|------|-----------|
| bridge-backend | 3001 | Yes |
| Bridge API (Docker) | 8000 | Yes |
| Redis | 6379 | Yes |
| Installer | 7777 | Yes |
| (Vite/dev) | 5173 | Yes |
| Dashboard | 3000 | No |
| frontend | 3020 | No |
| bridge-auth | 3030 | No |

---

## 4. Fixes applied during this run

- **scripts/port-handler.ps1:** Fixed PowerShell parse errors:
  - Replaced `<port>` in usage strings with single-quoted strings so `<` is not interpreted as redirection.
  - Replaced em dash (—) in double-quoted strings with ASCII hyphen (-) to avoid parser issues.
  - Simplified "Killing PID" line to use concatenation instead of nested `$()` in one string.

---

## 5. How to re-run

```powershell
# Audit
.\audit-wall.ps1

# Backend API tests
$env:PYTHONPATH = "e:\BridgeAI\BridgeLiveWall\backend"; python -m pytest tests/test_api.py -v

# Port status
.\scripts\port-handler.ps1 list
```

---

## 5. Install → Boot → Audit → Fix → Apply → Verify (loop until match)

- **install-all.ps1:** Installs Python backend deps (`backend/app/requirements.txt`), bridge-backend (`npm install`), and optional frontend. Run once or after pull.
- **run-full-loop.ps1:** Runs in order: (1) install-all, (2) add to boot (`install-startup.ps1`), (3) audit → fix (apply-keys) → re-audit until critical=0 or max rounds, (4) apply-keys, (5) state verify, (6) pytest. Exits 0 when audit 0 critical, state OK, tests pass.
  - `.\run-full-loop.ps1` — full run
  - `.\run-full-loop.ps1 -ApproveStateOnce` — allow state approve once if root mismatch
  - `.\run-full-loop.ps1 -SkipInstall -SkipBoot` — only audit/fix/apply/verify (e.g. after editing .env)

## 6. State verify & backend reload (0ok)

- **State mutation:** Generated files `audit-results.json` and `twin_wall.png` are excluded from the Merkle tree in `tools/state/verify.cjs`, so normal audit/wallpaper runs no longer cause root mismatch. If you still see "State mutation detected", approve once: `node tools/state/verify.cjs --approve`.
- **Uvicorn reload:** `run-backend.ps1` uses `--reload-dir backend` so only the backend tree is watched; changes under `bridge-backend/node_modules` or elsewhere no longer trigger reload and avoid Redis connection cancel during startup.

---

**Summary:** Audit shows **0 critical**; **27/27** API tests passed; bridge-backend, Bridge API (Docker), Redis, and Installer are listening. State verify and reload are configured so normal runs stay 0ok. Recommendations are optional (frontend/auth not running, DNS/R2, optional D: paths).
