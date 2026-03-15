# Scheduler — The Nervous System Pulse

The spine states: **Endpoint → Reducer → State → Scheduler → Expression**.

The Scheduler is the pulse. Without it, the spine is incomplete.

---

## Scheduler Responsibilities

| Responsibility | Trigger | Effect |
|----------------|---------|--------|
| **Evolution loops** | Periodic / on entropy threshold | Recognize → Reorder → Respond → Reflect |
| **Training cycles** | On sufficient samples / on entropy rise | Retrain emotion, reasoning models |
| **Decay** | On stress accumulation | Degradation logic, performance factor |
| **Mission audits** | Periodic / on drift | Validate alignment, trigger governance |

---

## Current State

**Organism mode: reactive.**

The system waits for input. No internal scheduler runs autonomously.

**Agentic mode** (future) requires:
- Internal goal vector in canonical state
- Background scheduler comparing `current_state` vs `goal_vector`
- Self-triggered reducers when delta exists
- Internal dissatisfaction as driver
- **Heartbeat:** Once seed capital threshold is met, schedule autonomous pulse (evolution, training, decay, mission audit)

Until then: **reactive architecture with structural discipline**.

---

## Entropy → Scheduler

When `system_entropy_score` rises:
- Trigger training
- Trigger optimization
- Trigger governance
- Trigger evolution loop

This is when organism metaphor becomes literal.

---

## Explicit Contract (When Implemented)

| Parameter | Value | Purpose |
|----------|-------|---------|
| **Tick interval** | 60s (configurable via `BRIDGE_SCHEDULER_TICK_SEC`) | Heartbeat cadence |
| **Max reducer executions per cycle** | 10 | Prevents runaway mutation |
| **Responsibilities** | evolution, training, decay, mission_audit | Per-tick eligibility |

```
GET  /api/scheduler/status   → { next_evolution, next_training, entropy, tick_interval_ms }
POST /api/scheduler/trigger  → { evolution | training | decay | audit } (orchestrator only)
```

**Who triggers evolution?** In reactive mode: external caller. In agentic mode: scheduler compares `current_state` vs `goal_vector`, invokes sanctioned reducer when delta > threshold.

---

**Signed:** Physiology Definition  
**Date:** 2025-02-15
