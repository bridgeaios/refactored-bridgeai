# Cortex Command Interface — Design (2026-03-17)

## Goal

Add a **single operator view** that exposes:

- live agent count (twins)
- task throughput + backlog
- revenue state (UBI/treasury/ops/founder buckets)
- swarm health score (0–1)
- top reputation (who to allocate work to)
- a safe control to “pump demand” when backlog is low

The outcome is **control visibility**, not just monitoring: operators can see whether the swarm is economically stable and can inject demand when needed.

## Placement

Ship the first version inside the existing **Agents** page: `frontend/public/agents.html`.

Rationale:
- It already polls `/api/live/report` and shows “Agents & Digital Twins”
- It’s an operator-oriented view (replication status, nodes, leaderboard)
- Lowest-change path (no new routing, no bundler work)

## Data Sources (Backend)

- **Live map/report**: `GET /api/live/report`
- **Revenue state**: `GET /api/revenue/status`
- **SDG/task counters**: `GET /api/sdg/metrics`
- **Swarm health**: `GET /api/swarm/health`
- **Reputation top**: `GET /api/reputation/top?limit=20`
- **Demand pump**: `POST /api/demand/pump` with `{ target_backlog, max_create }`

## UI Components

### 1) Command Summary Strip (KPI cards)

Cards (small, glanceable):
- **Swarm Health**: score + OK/Degraded tag
- **Twins**: count from live report
- **Marketplace**: open/in-progress/completed counts (derived from existing data where available)
- **Revenue**: total distributed + buckets (UBI/treasury/ops/founder)
- **Throughput**: `tasks_created`, `tasks_completed`, `trades_executed` from SDG metrics

### 2) Demand Controls (safe)

- inputs: target backlog, max create
- button: “Pump demand”
- renders result: created/skipped/open_tasks/target_backlog
- never loops automatically (human-triggered only)

### 3) Reputation Table

Top N agents:
- agent_id
- score
- success_rate
- latency_ms
- average_cost
- quality_score

## Refresh Strategy

- Poll every **10–15 seconds** (same cadence as existing page).
- Demand pump is user-triggered only.

## Failure Modes / Graceful Degradation

- If an endpoint is unavailable, render “offline” copy in that card/table but keep other panels updating.
- Keep HTML escaping on all user-provided strings (agent_id, node_id, etc).

## Follow-ups (not required for v1)

- Move page JS into `frontend/src/` and bundle (improves caching/maintainability).
- Add “allocation recommendation” button (choose best agent by reputation score).
- Wire real utilization/profitability inputs into `/api/swarm/health` (replace proxies).

