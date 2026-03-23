# Bridge AI OS — API Surface Operational Map

**Complete API surface with subsystem segmentation.**

---

## 1. Core System Layers (Control / Health)

| Endpoint | Function |
|----------|----------|
| `/api/health` | Basic health check |
| `/api/health/extended` | System stability, latency, error rate, integrity scoring |
| `/api/status` | Runtime status |
| `/api/telemetry` | Metrics emission |

---

## 2. Twin Engine (Decision Core)

| Endpoint | Function |
|----------|----------|
| `/api/twin/decide` | Deterministic action vs silence (admissible → action, otherwise → silence) |
| `/api/twin/simulate` | Stress testing |
| `/api/twin/evolve` | Governed evolution |
| `/api/twin/profile` | Full agent structure |
| `/api/twin/env-keys` | Capability readiness |

**Rule**: Binary decision operator — admissible → action; otherwise → silence.

---

## 3. Economic Engine (Revenue + UBI)

| Endpoint | Function |
|----------|----------|
| `/api/ubi/claim`, `/api/ubi/distribute` | UBI flow |
| `/api/treasury/*` | collect, ledger, disburse, status |
| `/api/revenue/status` | Revenue engine status |

**Function**: Converts system activity → value. Enforces risk governors + exposure limits.

---

## 4. Marketplace (Work Generation Loop)

| Endpoint | Function |
|----------|----------|
| `/api/marketplace/tasks` | List tasks (sorted by priority) |
| `/api/marketplace/task` | Create task |
| `/api/marketplace/accept` | Accept task |
| `/api/marketplace/complete` | Complete task |
| `/api/marketplace/pledge` | Pledge to upliftment task |

**Closed loop**: Task created → Assigned (human or twin) → Completed → Revenue + reputation updated.

**Priority routing**: `priority_score = (reward * urgency * trust) / latency_cost`

---

## 5. Swarm / Replication

| Endpoint | Function |
|----------|----------|
| `/api/twins/*` | allocate, teach, leaderboard |
| `/api/replication/*` | Status, nodes |
| `/api/swarm/health` | Swarm health score |

**Function**: Horizontal scaling, skill propagation, network growth.

---

## 6. Live System + Orchestration

| Endpoint | Function |
|----------|----------|
| `/api/live/map` | Real-time system map |
| `/api/live/report` | Live report |
| `/api/orchestrate/directives` | Execution instructions (non-autonomous trigger layer) |

---

## 7. Sensors → Monetization Bridge

| Endpoint | Function |
|----------|----------|
| `/api/sensors/mouse` | Mouse activity |
| `/api/sensors/wifi` | WiFi presence |

**Insight**: Raw activity → auto-task creation → micro-earnings (passive income instrumentation).

---

## 8. Speech + Embodiment Layer

| Endpoint | Function |
|----------|----------|
| `/api/speech/reason` | Intent reasoning |
| `/api/speech/embody` | Emotion, response |
| `/api/tts` | Text-to-speech |

**Pipeline**: Input → intent → emotion → response → phonemes → audio.

---

## 9. System Intelligence / Governance

| Endpoint | Function |
|----------|----------|
| `/api/system/comprehension/*` | Alignment enforcement |
| `/api/audit/drift` | Drift detection |

**Function**: Controlled evolution, alignment.

---

## 10. External Integration

- Payments: Paystack, PayPal, Crypto webhooks
- Google Sheets read/write
- SIWE auth
- Project registry (`/api/projects/*`)

---

## 11. CLI + Execution Layer

| Endpoint | Function |
|----------|----------|
| `/api/cli/*` | Queue-based execution, external runners |

---

## 12. State Engine (Critical Backbone)

| Endpoint | Function |
|----------|----------|
| `/api/state` | Mutate via reducers |
| `/api/state/snapshot` | Full state |
| `/api/state/reducers` | Reducer registry |

**Architecture**: Endpoint → Reducer → State → Scheduler → Expression

**Rule**: No arbitrary mutation; full determinism.

---

# System Truth (Condensed)

**A self-regulating economic AI organism**

| Layer | Function |
|-------|----------|
| **Perception** | Sensors, speech, inputs |
| **Decision** | Twin engine (binary admissibility) |
| **Action** | Marketplace + CLI |
| **Value extraction** | Treasury + UBI |
| **Replication** | Swarm + twins |
| **Governance** | System comprehension + drift control |

---

# Gaps (High Impact)

1. No explicit **rate limiter layer** exposed
2. No **auth segmentation per endpoint class** (only SIWE global)
3. ~~No **priority scheduler** for task routing~~ → **Implemented** (see `task_priority` module)
4. Missing **failure recovery / rollback endpoints**
5. No explicit **data lake / historical analytics endpoint**

---

# Priority Routing (Canonical — Governing Law)

**Formula**:
```
priority_score = (reward * urgency * trust) / max(1, latency_cost)
```

**Priority = governing law of execution. No bypass. Canonical ordering.**

- **Trust normalization**: `trust = min(1.0, max(0.1, reputation))` — prevents exploit
- **Dual mode**: `_priority_locked` (audit + treasury baseline) set at creation; `_priority_live` (routing)

**Applied to**:
- `GET /api/marketplace/tasks?twin_id=` — **required** twin_id; always sorted by priority
- `POST /api/twins/allocate` — **top task only**; no manual task_id; Execution = argmax(priority)
- `POST /api/marketplace/accept` — backpressure: reject if score < GLOBAL_MIN
- `POST /api/marketplace/complete` — **payout = _priority_locked × quality**
- `POST /api/demand/pump` — priority-aware: throttle when avg ≥ TARGET_PRIORITY
- State snapshot — `priority_distribution`: p50, p90, min, max

**Backpressure**: `GLOBAL_MIN_PRIORITY` = 0.15 (env: `BRIDGE_PRIORITY_MIN_THRESHOLD`)

**Orchestrator**: `.\scripts\orchestrate-api-mesh.ps1 -Execute` — allocates top task when score > 0.2
