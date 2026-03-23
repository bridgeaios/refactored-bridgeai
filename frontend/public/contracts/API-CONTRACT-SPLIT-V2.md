# API Contract Split V2

- V1 canonical paths: 29
- Runtime paths: 109
- V2 public paths: 75
- Internal paths: 38

## Decision

Promoted product and integration endpoints into `openapi.v2.public.json` and left orchestration, ingestion, operational control, and admin endpoints in `openapi.internal.json`.

## Promoted Runtime Paths

- `/api/audit/drift` [get]
- `/api/auth/siwe` [post]
- `/api/capabilities` [get]
- `/api/econ/weights` [get]
- `/api/founder-todo` [get]
- `/api/health/extended` [get]
- `/api/live/map` [get]
- `/api/live/report` [get]
- `/api/projects` [get]
- `/api/projects/register` [post]
- `/api/projects/{project_id}` [get]
- `/api/projects/{project_id}/heartbeat` [post]
- `/api/replication/nodes` [get]
- `/api/replication/status` [get]
- `/api/reputation/top` [get]
- `/api/sensors/mouse` [get]
- `/api/sensors/wifi` [get]
- `/api/skills/definitions` [get]
- `/api/skills/learn-from-youtube` [post]
- `/api/skills/youtube-recommend/{skill_id}` [get]
- `/api/skills/youtube-search` [get]
- `/api/state/reducers` [get]
- `/api/state/snapshot` [get]
- `/api/status` [get]
- `/api/svg-build/history` [get]
- `/api/swarm/health` [get]
- `/api/system/comprehension` [get]
- `/api/system/comprehension/check-alignment` [post]
- `/api/system/comprehension/explain` [get]
- `/api/system/comprehension/operational-model` [get]
- `/api/system/comprehension/role-awareness` [get]
- `/api/system/comprehension/skill` [get]
- `/api/telemetry` [get]
- `/api/telemetry/events/svg-build` [get]
- `/api/treasury/controls` [get]
- `/api/treasury/ledger` [get]
- `/api/treasury/rails` [get]
- `/api/treasury/status` [get]
- `/api/treasury/summary` [get]
- `/api/tts/available` [get]
- `/api/twin/env-keys` [get]
- `/api/twins` [get]
- `/api/twins/leaderboard` [get]
- `/api/user/settings` [get, put]
- `/api/wiki/registry` [get]
- `/health` [get]

## Mixed Visibility Paths

- `/api/econ/weights` public=['get'] internal=['post']
- `/api/projects/{project_id}` public=['get'] internal=['delete']
- `/api/sensors/mouse` public=['get'] internal=['post']
- `/api/sensors/wifi` public=['get'] internal=['post']

## Internal-only Groups

- CLI and worker control
- Ingest and operational triggers
- Payment webhooks and treasury mutation endpoints
- Replication registration and twin mutation helpers
- Sensor ingestion POST endpoints
- Governance and economic mutation endpoints

## Artifacts

- `openapi.v2.public.json`
- `openapi.internal.json`
- `docs/api-contract-split-v2.json`