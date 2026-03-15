# Bridge AI OS — Structural Spine

**Version:** 1.0.0  
**Status:** Canonical  
**Purpose:** The architectural essence of Bridge AI OS — the perception-aligned, state-driven control surface for a digital organism.

---

## Core Axiom

> The system isn't just serving data. It is modeling an organism.

---

## Gravitational Structure (Cortex)

**Single orchestrator layer.** Endpoints do not act like independent services.

| Layer | Responsibility |
|-------|----------------|
| **Cortex** | Receives requests → validates mission alignment → enforces risk → routes to modules → state mutation only via reducers |
| **Externally** | Minimal API surface |
| **Internally** | Strict routing control |

**Capability Registry** — Twins read flags before acting. Scale to 100 variants.

```json
{ "perception": true, "speech": true, "trade": true, "ubi": true, "simulate": true, "evolution": true, "marketplace": true, "state_mutation": true }
```

**Capability Lock** — `BRIDGE_CAP_LOCK=1` freezes capabilities at boot. No runtime override. Prevents production drift.

**Authority Classes** — Absolute enforcement. No privilege bleed.

| Class | Scope |
|-------|-------|
| **public** | read-only + speech |
| **economic** | marketplace + ubi + trade |
| **internal** | + state mutation |
| **orchestrator** | + evolution, system |

**Normalized Response** — Predictable. Reduces entropy.

```json
{ "ok": true, "data": {}, "meta": { "confidence": 1, "silence": false, "state_delta": false } }
```

**Silence** — First-class. Not null. Strategic output.

**State Versioning** — Every mutation increments. Replay. Audit. Rollback.

**Layer Modes** — Real-time (speech, emotion, state) vs Strategic (simulation, training, evolution). Different schedulers. Different compute budgets.

---

## System Physics — Governance, Resilience, Scaling

| Physics | Purpose |
|---------|---------|
| **Determinism** | Same inputs + state → same output. `BRIDGE_DETERMINISTIC=1`. Auditability. |
| **Event Bus** | Endpoint → Event → Reducer → State → Subscribers. Loose coupling. |
| **Failure Modes** | TTS fails → phonemes only. Emotion fails → neutral. Graceful degradation. |
| **Observability** | decision_latency, speech_latency, silence_rate, state_mutation_frequency, economic_conversion_rate. `GET /api/telemetry`. |
| **Economic Risk Governor** | Max exposure per twin. Cooldown timers. `BRIDGE_MAX_EXPOSURE`, `BRIDGE_ECONOMIC_COOLDOWN`. |
| **Identity Immutability** | core_values, mission_alignment, authority_class — immutable. skill_stack, state, emotion — mutable. |
| **Ethical Conflict** | Scan before execute. Conflict > threshold → silence. `BRIDGE_ETHICAL_THRESHOLD`. |
| **Degradation** | Stress accumulation, cognitive load, performance decay under pressure. |
| **Simulation Isolation** | Simulation state ≠ live canonical state. `committed: false` unless explicitly committed. |
| **Upgrade Governance** | Proposal → Validation → Sandbox → Commit. No direct evolution to production. |
| **Evolution Energy Budget** | Each evolve consumes budget. Replenished via: training completion, economic surplus, governance approval. `BRIDGE_EVOLUTION_BUDGET`. |
| **Drift Detection** | Periodic audit: compare state to baseline mission vector. If drift > threshold → governanceVote or training. `GET /api/audit/drift`. `BRIDGE_DRIFT_THRESHOLD`. |
| **State Snapshot** | `GET /api/state/snapshot` — state, state_version, state_hash. Version without snapshot is memory without recall. |
| **Monotonic Versioning** | Redis INCR for cluster-safe ordering. Organisms need synchronized time. |
| **Cold-Start Identity Lock** | SPINE + reducers + schema checksum. If changed without version bump → refuse start. `BRIDGE_IDENTITY_LOCK`. |
| **Confidence Floor** | If confidence < threshold → force silence. `BRIDGE_CONFIDENCE_FLOOR`. |
| **Capability Audit Log** | Every override logged: timestamp, capability, old/new value, actor. |
| **Economic Circuit Breaker** | Trade frequency or entropy exceeds threshold → disable trade. `BRIDGE_CB_TRADE_FREQ`, `BRIDGE_CB_ENTROPY`. |
| **Extended Health** | `GET /api/health/extended` — composite health score. One number: is the organism stable? |
| **Determinism Replay** | `deterministic_seed` + `state_version` in meta. Log seed per decision. Replay = science. |
| **Event Backpressure** | Max queue size, drop policy (oldest/newest). `event_backlog_depth` in telemetry. |
| **Degradation Tiering** | Level 0–3: full, partial (no audio), minimal (text only), silent. Exposed in telemetry. |
| **Baseline Drift** | `baseline_silence_rate`, `baseline_latency`, `baseline_economic_conversion`. Emit `system_drift` when deviation > threshold. |
| **Global Exposure** | `BRIDGE_GLOBAL_EXPOSURE` — aggregate exposure across twins. Markets don't care about instance boundaries. |
| **Identity Seal** | `identity_hash = SHA256(core_values + mission_alignment + authority_class)`. Expose in root. |
| **Ethical Explainability** | `meta.ethical_score`, `meta.ethical_reason` — inspectable categories. |
| **Recovery Curve** | Stress decays over time. `BRIDGE_RECOVERY_RATE`. Biology heals. |
| **Simulation Commit Guard** | Orchestrator + explicit flag. Governance vote if affecting immutable. |
| **Upgrade Rollback** | Snapshot before commit. Auto rollback if post-commit telemetry degrades. |

---

## The Flow

```
Endpoint → Reducer → State → Scheduler → Expression
```

All meaningful change flows through this pipeline. No rogue mutation. Controlled evolution.

---

## Structural Principles

| Principle | Meaning |
|-----------|---------|
| **All action passes through explicit reducers** | No direct state mutation. Every change is a sanctioned reducer. |
| **All speech passes through embodiment** | Transcript → Reasoning → Embodiment → Phonemes/Visemes/Audio. Never raw execution. |
| **All identity is inspectable** | Twin profile, skill stack, risk model, blind spots, upgrade path — meta-cognition exposed as API. |
| **All evolution is state-bound** | Adaptive loop: Recognize → Reorder → Respond → Reflect. Ingest feedback. State-bound. |

**Auditable. Composable. Dangerous if misaligned — powerful if constrained.**

---

## Silence Discipline (Constitutional)

> **If value ≤ 0 → Return silence.**

This is law. Not suggestion.

The decision engine must not return action when no positive-value output exists. Future contributors must not dilute this. Silence is strategic output. Silence is not null.

---

## Top-Level Surface

### 1. Infrastructure
- **Root** — Service metadata, operational status
- **Health** — Liveness check

### 2. Canonical State Mutation
- **POST /api/state** — All meaningful change flows through sanctioned reducers
- Body: `{ reducer, payload?, authToken? }`
- Broadcasts to WebSocket clients
- No rogue mutation

### 3. Mission Tracking
- **Backlog → In Progress → Review → Done**
- Counts exposed via `/api/mission/board`

### 4. Skill Ingestion
- Structured capability expansion
- POST `/api/skills`

### 5. Shared Twin Document
- **XML** — Canonical embodiment record (mission, face_state, authority)
- GET/POST `/api/twin/shared-xml`

### 6. Deep Twin Profile
- Identity, cognitive bias, skill stack, risk model, blind spots, upgrade path
- Meta-cognition exposed as API
- GET `/api/twin/profile`

### 7. Decision Engine
- Environment + goals + constraints + risk threshold + candidate actions
- → Action or silence
- POST `/api/twin/decide`

### 8. Simulation Engine
- Stress-test behavior under uncertainty, pressure, loss, opportunity
- POST `/api/twin/simulate`

### 9. Evolution Loop
- Adaptive updating of the twin
- POST `/api/twin/evolve`

### 10. Speech Stack
- **Reasoning** — Intent, emotion, urgency, plan
- **Embodiment** — Phonemes, visemes, prosody, audio
- **Memory** — Dialogue history
- **Emotion** — Computation layer
- **TTS** — Streaming

### 11. Training Lifecycle
- Start, status
- POST `/api/train/start`, GET `/api/train/status`

### 12. Infrastructure Awareness
- eSIM status
- GET `/api/esim/status`

### 13. Economic Layer
- **UBI** — Claiming system
- **Marketplace** — Task creation, acceptance, reward economy
- **SDG** — Measurable impact
- **Revenue** — Financial feedback (UBI, treasury, ops, founder)
- **BossBots** — Signal execution

---

## Convergence

> The system treats intelligence as **stateful**, **embodied**, **economically interactive**, and **evolution-capable**.

It is not a chatbot API.  
It is a **control surface for a digital organism**.

---

## Reactive vs Agentic

**Current: Reactive.**

The system waits for input. Responds only to requests. No internal scheduler.

**Agentic** requires:
- Goal vector stored in canonical state
- Background scheduler comparing `current_state` vs `goal_vector`
- Self-triggered reducers when delta exists
- Internal dissatisfaction as driver

Until then: **advanced reactive organism**. Not a flaw — clarity.

The root endpoint exposes `organism_mode: "reactive"` explicitly.

---

## References

- [CONTRACTS.md](./CONTRACTS.md) — API contracts
- [SCHEDULER.md](./SCHEDULER.md) — Scheduler responsibilities, reactive vs agentic
- [system_comprehension.md](./system_comprehension.md) — Structural mapping
- [cognitive_twin.md](./cognitive_twin.md) — Decision engine, simulation, evolution
- [speech_embodiment.md](./speech_embodiment.md) — Speech stack
