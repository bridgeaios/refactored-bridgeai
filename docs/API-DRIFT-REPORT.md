# API Drift Report

- Canonical contract paths: 29
- Runtime route paths: 109
- Exact overlap: 29
- Canonical-only: 0
- Runtime-only: 80

## Decision

Expanded the contract surface instead of trimming the backend. Trimming would remove live capabilities and risk frontend regressions. The canonical 29-path contract remains the stable curated surface; the runtime supplement documents the additional implemented endpoints.

## Runtime-only Endpoints

### Skills and Learning

- `/api/skills/definitions` [get]
- `/api/skills/learn-from-youtube` [post]
- `/api/skills/youtube-recommend/{skill_id}` [get]
- `/api/skills/youtube-search` [get]

### User and Health

- `/api/capabilities` [get]
- `/api/health/extended` [get]
- `/api/state/reducers` [get]
- `/api/state/snapshot` [get]
- `/api/status` [get]
- `/api/telemetry` [get]
- `/api/user/settings` [get, put]
- `/health` [get]

### Live Ops and Sensors

- `/api/live/map` [get]
- `/api/live/report` [get]
- `/api/orchestrate/directives` [get]
- `/api/sensors/mouse` [get, post]
- `/api/sensors/wifi` [get, post]
- `/api/svg-build/history` [get]
- `/api/telemetry/events` [post]
- `/api/telemetry/events/svg-build` [get]
- `/api/wiki/registry` [get]

### Twins and System

- `/api/audit/drift` [get]
- `/api/system/comprehension` [get]
- `/api/system/comprehension/check-alignment` [post]
- `/api/system/comprehension/evolve` [post]
- `/api/system/comprehension/explain` [get]
- `/api/system/comprehension/operational-model` [get]
- `/api/system/comprehension/role-awareness` [get]
- `/api/system/comprehension/skill` [get]
- `/api/twins` [get]
- `/api/twins/allocate` [post]
- `/api/twins/auto-add` [post]
- `/api/twins/leaderboard` [get]
- `/api/twins/teach` [post]

### Economy and Treasury

- `/api/demand/pump` [post]
- `/api/econ/circuit-breaker` [get]
- `/api/econ/reset-breaker` [post]
- `/api/econ/weights` [get, post]
- `/api/marketplace/complete` [post]
- `/api/marketplace/pledge` [post]
- `/api/payments/webhook/crypto` [post]
- `/api/payments/webhook/paypal` [post]
- `/api/payments/webhook/paystack` [post]
- `/api/payments/webhook/{rail}` [post]
- `/api/reputation/top` [get]
- `/api/swarm/health` [get]
- `/api/treasury/collect` [post]
- `/api/treasury/controls` [get]
- `/api/treasury/disburse` [post]
- `/api/treasury/ingest` [post]
- `/api/treasury/ledger` [get]
- `/api/treasury/rails` [get]
- `/api/treasury/status` [get]
- `/api/treasury/summary` [get]
- `/api/ubi/distribute` [post]

### Speech and TTS Extensions

- `/api/tts/available` [get]

### Founder and Integrations

- `/api/auth/siwe` [post]
- `/api/cli/enqueue` [post]
- `/api/cli/history` [get]
- `/api/cli/queue/next` [get]
- `/api/cli/report` [post]
- `/api/cli/status` [get]
- `/api/founder-todo` [get]
- `/api/founder-todo/{obj_id}/complete` [patch]
- `/api/google-sheets/{spreadsheet_id}/append` [post]
- `/api/google-sheets/{spreadsheet_id}/info` [get]
- `/api/google-sheets/{spreadsheet_id}/read` [get]
- `/api/google-sheets/{spreadsheet_id}/write` [post]
- `/api/projects` [get]
- `/api/projects/register` [post]
- `/api/projects/{project_id}` [delete, get]
- `/api/projects/{project_id}/heartbeat` [post]

## Canonical-only Endpoints

- None

## Artifacts

- `openapi.json`: curated canonical 29-path contract
- `openapi.runtime-expanded.json`: full runtime-derived contract for all live registered routes
- `openapi.runtime-supplement.json`: runtime-only endpoints not present in the canonical contract
- `docs/api-drift-report.json`: machine-readable drift summary
