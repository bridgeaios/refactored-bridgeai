# Bridge AI OS — Phase 3 API Contracts

**Status:** FROZEN  
**Effective:** 2025-02-15  
**Version:** 1.0

## Scope

This document defines the formal API contracts between the Bridge AI OS backend and frontend. All endpoints, request/response shapes, and error codes are committed for Phase 3.

**Architectural spine:** See [SPINE.md](./SPINE.md) — Endpoint → Reducer → State → Scheduler → Expression.

---

## Contract Categories

### 1. Core Infrastructure

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/` | GET | Returns `{ service, docs, health, frontend }` |
| `/api/health` | GET | Returns `{ ok: boolean }` |
| `/api/health/extended` | GET | Returns `{ ok, health_score, components }` — composite organism stability |
| `/api/state` | POST | Body: `{ reducer: string, payload?: object, authToken?: string }` → `{ ok: boolean }` |
| `/api/state/reducers` | GET | Returns immutable snapshot: `{ version, reducers, reducer_names, checksum, strict_mode, spine, identity_hash }` |
| `/api/state/snapshot` | GET | Returns `{ state, state_version, state_hash }` — full state recall |

### 2. Mission & Skills

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/api/mission/board` | GET | Returns `{ backlog, in_progress, review, done }` (numbers) |
| `/api/skills` | POST | Body: `{ name: string, tags: string[], description?: string }` → `{ ok: boolean }` |

### 3. Digital Cognitive Twin

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/api/twin/shared-xml` | GET | Returns `application/xml` — canonical Twin document |
| `/api/twin/shared-xml` | POST | Body: valid XML string → `{ ok: boolean }` |
| `/api/twin/profile` | GET | Returns Twin Profile: identity, skill_stack, decision_model, adaptive_loop, risk_model, communication_style, blind_spots, upgrade_path |
| `/api/twin/decide` | POST | Body: `{ environment, goal_vector, constraints, risk_threshold, candidates }` → `{ action, reason? }` or `{ action: null, reason }` |
| `/api/twin/simulate` | POST | Body: `{ uncertainty, pressure, loss, opportunity }` → simulation result object |
| `/api/twin/evolve` | POST | Body: `{ feedback?, evolution_mode?, authToken: "orchestrator" }` → evolution state. Requires orchestrator + evolution budget. |

### 4. Speech & Embodiment

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/api/speech/reason` | POST | Body: `{ transcript?, text?, context? }` → `{ normalized_text, intent, topic, emotion, urgency, confidence, clarification_needed, response, execution_plan? }` |
| `/api/speech/embody` | POST | Body: `{ transcript?, prompt?, text?, context?, audience_model? }` → `{ response, phonemes, emotion, prosody, audio_base64?, silence, confidence, execution_plan?, viseme_map }` |
| `/api/speech/embody/speak` | POST | Body: `{ text }` → `{ response, phonemes, emotion, audio_base64?, viseme_map }` |
| `/api/speech/embodiment/skill` | GET | Returns skill definition object |
| `/api/speech/embodiment/memory` | GET | Returns `{ history }` |
| `/api/speech/embodiment/memory/clear` | POST | → `{ ok: boolean }` |
| `/api/tts` | POST | Body: `{ text, voice_id? }` → `audio/mpeg` stream |

### 5. Economic & Marketplace

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/api/ubi/claim` | POST | Body: `{ address: string }` → `{ amount: number }` |
| `/api/marketplace/tasks` | GET | Returns task array |
| `/api/marketplace/task` | POST | Body: `{ title?, desc?, reward?, ... }` → `{ status: "created", task }` |
| `/api/marketplace/accept` | POST | Body: `{ task_id, wallet }` → `{ status: "accepted", task }` |
| `/api/sdg/metrics` | GET | Returns metrics object |
| `/api/revenue/status` | GET | Returns revenue status object |
| `/api/bossbots/trade` | POST | Body: `{ asset: string }` → `{ signal }` |
| `/api/bossbots/signals` | GET | Returns signals array |

### 6. Emotion & Learning

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/api/emotion/compute` | POST | Body: emotion inputs (votes, backlog, in_progress, sentiment, etc.) → emotion record |
| `/api/train/start` | POST | → `{ started: boolean }` |
| `/api/train/status` | GET | Returns training status object |
| `/api/esim/status` | GET | Returns eSIM status object |

### 7. Audit & Drift

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/api/audit/drift` | GET | Returns `{ drift_score, threshold, should_trigger_governance, mission_board }` — immune system logic |
| `/api/telemetry` | GET | Returns `{ decision_latency_*, speech_latency_*, silence_rate*, evolution_budget_remaining, ... }` |

---

## Error Contracts

| Code | Condition |
|------|-----------|
| 400 | Missing required field (e.g. `reducer`, `address`, `text`, `task_id`, `wallet`, `asset`) |
| 404 | Resource not found (e.g. task not available) |
| 422 | Validation error (Pydantic) — `{ detail: ValidationError[] }` |
| 503 | Service unavailable (e.g. TTS provider down) |

---

## WebSocket Contract

| Path | Purpose |
|-----|---------|
| `/ws/{channel}` | State sync, transcript→response flow |

**Message types:**
- `hello` → `welcome` with `ts`
- `transcript` / `prompt` → `response` with `response`, `emotion_state`, `topic`, `reasoning`
- `stateMutation` broadcast to clients

---

## Commitments

1. **Backward compatibility:** New fields may be added; existing fields will not be removed or renamed without a major version bump.
2. **Schema source:** `openapi.json` is the canonical schema; this document is the human-readable summary.
3. **Tests:** `tests/test_api.py` validates core contract compliance.

---

**Signed:** Phase 3 Contract Finalization  
**Date:** 2025-02-15
