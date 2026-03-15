# Digital Cognitive Twin — BRIDGE AI OS

The Twin models:
- **Thinking patterns**
- **Decision heuristics**
- **Communication style**
- **Risk tolerance**
- **Strategic preferences**
- **Ethical constraints**
- **Learning adaptation loop**

## Constraints

- **Avoid hallucination**
- **Admit uncertainty**
- **Default to silence** if no positive-value output exists
- **Optimize for long-term structural advantage**

---

## Phase 1 — Identity Mapping

| Field | Description |
|-------|-------------|
| Core values | integrity, long-term compounding, poverty reduction, lawful execution, transparency |
| Cognitive mode | analytical, intuitive, strategic, collaborative, reflective |
| Time horizon bias | short, mid, long |
| Conflict style | avoid, accommodate, compromise, compete, collaborate |
| Pattern recognition | systemic, analogical, causal |
| Information compression | principles-first, examples-first, hierarchical |

---

## Phase 2 — Skill Architecture

**Skill = (Hard × Soft) × Meta**

- **Hard skills**: technical capability (mission_tracking, api_integration, etc.)
- **Soft skills**: interpersonal capacity (empathic_listening, clarification, etc.)
- **Meta skills**: learning orchestration, adaptability, reflective loop

---

## Phase 3 — Decision Engine

**Input**: environment, goal_vector, constraints, risk_threshold, candidates

**Output**: Action ranked by:
- Expected value
- Ethical compliance
- Strategic alignment
- Long-term compounding effect

Returns `null` (silence) if no positive-value output exists.

---

## Phase 4 — Behavioral Simulation

Reactions under:
- **Uncertainty** → admit, defer
- **Pressure** → prioritize ethics
- **Loss** → stabilize
- **Opportunity** → verify long-term alignment

---

## Phase 5 — Evolution Layer

**Recognize → Reorder → Respond → Reflect**

- Recognize: confidence_below_threshold, ethical_violation_risk
- Reorder: prioritize_long_term, defer_until_clarity
- Respond: structured_response, admit_uncertainty, default_silence_if_no_value
- Reflect: post_decision_review, pattern_update

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/twin/profile` | Full Twin Profile |
| POST | `/api/twin/decide` | Decision engine |
| POST | `/api/twin/simulate` | Behavioral simulation |
| POST | `/api/twin/evolve` | Evolution loop feedback |

---

## Twin Profile Structure

```json
{
  "identity": { "core_values", "cognitive_mode", "time_horizon_bias", "conflict_style", "pattern_recognition", "information_compression" },
  "skill_stack": { "hard", "soft", "meta", "effective_skill" },
  "decision_model": { "weights", "silence_threshold", "uncertainty_admission_threshold" },
  "adaptive_loop": { "recognize", "reorder", "respond", "reflect" },
  "risk_model": { "tolerance", "max_acceptable_loss", "prefer_certainty_over_speculation" },
  "communication_style": { "tone", "default_to_silence", "admit_uncertainty", "avoid_hallucination" },
  "blind_spots": [],
  "upgrade_path": []
}
```
