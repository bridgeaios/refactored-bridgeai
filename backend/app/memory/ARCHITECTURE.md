# Phase 2.3: Memory Intelligence — System Architecture

## Overview

Memory Intelligence transforms EHSA from a reactive executor into a **learning system** that:

- **Learns** from every execution trace
- **Predicts** what users will do next
- **Optimizes** plans based on history
- **Improves** with every interaction

### The Learning Loop

```
EHSA Execution
    ↓
ExecutionTrace
    ↓
Learning System
    ├─ Pattern Extraction
    ├─ Prediction Engine
    ├─ Optimization Strategy
    └─ Feedback Loop
    ↓
Enhanced EHSA
    ├─ Preload Tools
    ├─ Optimize Plan
    └─ Faster Execution
    ↓
Better Outcomes
```

---

## Memory Architecture

### 5-Layer Memory System

```
┌─────────────────────────────────────────────┐
│ SHORT-TERM MEMORY                           │
│ (Session-level, Redis, volatile)            │
│ Last N executions for immediate context     │
├─────────────────────────────────────────────┤
│ LONG-TERM MEMORY                            │
│ (Historical, Database, persistent)          │
│ Compressed execution summaries               │
├─────────────────────────────────────────────┤
│ PATTERN LAYER                               │
│ Derived insights: "analyze → report: 85%"   │
├─────────────────────────────────────────────┤
│ PREDICTION LAYER                            │
│ Forecasts: "Next: generate_report (0.82)"   │
├─────────────────────────────────────────────┤
│ OPTIMIZATION LAYER                          │
│ Strategies: "Use tool order X, skip Y"      │
└─────────────────────────────────────────────┘
```

---

## Core Components

### 1. Models (`models.py`)

**ExecutionTrace**
```python
@dataclass
class ExecutionTrace:
    execution_id: str
    user_id: str
    goal: str
    steps: list[dict]  # Tool sequence
    outcome: str       # "success" | "partial" | "failed"
    duration_ms: float
    timestamp: float
```

**BehavioralPattern**
```python
pattern = {
    "pattern": "analyzer → reporter",
    "frequency": 12,       # Seen 12 times
    "confidence": 0.87,    # 87% chance this appears again
    "success_rate": 0.92,  # Succeeds 92% of the time
    "avg_duration_ms": 250,
}
```

**Prediction**
```python
prediction = {
    "next_action": "generate_report",
    "confidence": 0.82,
    "based_on_pattern": "analyzer → reporter",
}
```

**OptimizationStrategy**
```python
strategy = {
    "preferred_tool_order": ["analyzer", "reporter"],
    "preload_tools": ["analyzer", "reporter"],
    "expected_duration_ms": 250,
}
```

### 2. Pattern Extraction (`pattern_extraction.py`)

**Process**:
1. Ingest execution trace
2. Extract tool sequence
3. Calculate frequency and confidence
4. Track success rates
5. Store high-confidence patterns

**Example**:
```python
# After 5 successful executions of: analyzer → reporter
pattern = {
    "frequency": 5,
    "confidence": 0.83,      # 5/6 = 0.83
    "success_rate": 1.0,     # 5/5 successful
    "is_high_confidence": True,  # confidence > 0.7 AND frequency >= 5
}
```

**API**:
```python
extractor = PatternExtractor()

# Add trace
extractor.add_trace(user_id, trace)

# Get patterns
patterns = extractor.extract_high_confidence_patterns()
patterns = extractor.get_patterns_for_user(user_id, min_confidence=0.7)
patterns = extractor.get_most_frequent_patterns(user_id, limit=10)
patterns = extractor.get_most_successful_patterns(user_id, limit=10)

# Stats
stats = extractor.get_pattern_stats(user_id)
```

### 3. Prediction Engine (`prediction_engine.py`)

**Algorithm**:
1. Get current goal/input
2. Find matching patterns
3. Extract most likely next step
4. Calculate confidence

**Example**:
```python
# User says: "Analyze leads"
# Planner sees pattern: analyzer → reporter (0.87 confidence)
# Engine predicts: Next action = reporter
# Result: Preload reporter tool

prediction = engine.predict_next_action(
    user_id="user_123",
    current_goal="Analyze leads",
    patterns=[...],
)
# → Prediction(next_action="reporter", confidence=0.82)
```

**API**:
```python
engine = PredictionEngine()

# Make prediction
prediction = await engine.predict_next_action(user_id, goal, patterns)

# Preload hints
tools = engine.get_preload_hints(user_id, goal, patterns)

# Predict next goal
next_goal = engine.predict_next_goal(user_id, current_sequence, patterns)
```

### 4. Learning System (`learning_system.py`)

**Core responsibility**: Orchestrate all learning components

**Main Flow**:
```python
# 1. Ingest trace
await learning.learn_from_trace(trace)
    ├─ Updates short-term memory
    ├─ Extracts patterns
    └─ Updates statistics

# 2. Make prediction
prediction = await learning.make_prediction(user_id, goal)
    ├─ Gets user's patterns
    └─ Returns forecast

# 3. Optimize plan
optimized = await learning.optimize_plan(user_id, goal, plan)
    ├─ Finds matching patterns
    └─ Reorders steps for success

# 4. Provide feedback
await learning.provide_feedback(feedback)
    ├─ Reinforces successful patterns
    └─ Penalizes failures
```

**API**:
```python
learning = LearningSystem()

# Core methods
await learning.learn_from_trace(trace)
await learning.make_prediction(user_id, goal)
await learning.optimize_plan(user_id, goal, plan)
await learning.provide_feedback(feedback)

# Queries
memory = learning.get_memory(user_id)
stats = learning.get_learning_stats(user_id)
hints = learning.get_preload_hints(user_id, goal)

# Maintenance
await learning.decay_memory(user_id)  # Remove stale patterns
```

### 5. Enhanced EHSA (`ehsa_enhanced.py`)

**Upgrade over Phase 2.2 EHSA**:

```python
# Phase 2.2: Static execution
result = await ehsa.execute(goal, context, authority)

# Phase 2.3: Learning-driven execution
result = await ehsa.execute_with_learning(
    goal=goal,
    user_id=user_id,  # NEW: Per-user learning
    twin_context=context,
    authority=authority,
    learning_callback=on_learning_update,  # NEW: Track learning
)
```

**New Methods**:
```python
# Get insights about a user's learning
insights = await ehsa.get_twin_insights(user_id)

# Get proactive recommendation for next action
suggestion = await ehsa.suggest_next_action(user_id)
```

---

## Learning Flow

### Step 1: Execution

```python
result = await ehsa.execute_with_learning(
    goal="Analyze leads and generate report",
    user_id="user_123",
    ...
)
```

### Step 2: Trace Collection

EHSA creates ExecutionTrace:
```
ExecutionTrace:
  - execution_id: "exec_123"
  - user_id: "user_123"
  - goal: "Analyze leads and generate report"
  - steps: [
      {"tool_id": "crm.analyze", "status": "success"},
      {"tool_id": "analytics.report", "status": "success"},
    ]
  - outcome: "success"
  - duration_ms: 250
```

### Step 3: Pattern Learning

Learning system processes trace:
```python
await learning.learn_from_trace(trace)
```

Result:
```
Pattern Created/Updated:
  - pattern: "crm.analyze → analytics.report"
  - frequency: 1 (or incremented)
  - success_rate: 100%
  - confidence: 0.2 (1/6)
```

### Step 4: Prediction

Next time user says "Analyze leads":
```python
prediction = await learning.make_prediction(
    user_id="user_123",
    goal="Analyze leads"
)
# → Prediction(next_action="analytics.report", confidence=0.82)
```

### Step 5: Optimization

EHSA optimizes plan:
```python
optimized = await learning.optimize_plan(
    user_id="user_123",
    goal="Analyze leads and generate report",
    current_plan=[...]
)
# Reorder steps to match successful pattern
```

### Step 6: Execution with Optimizations

```python
# Preload tools
preload = learning.get_preload_hints(user_id, goal)
# → ["analytics.report"]

# Execute optimized plan
result = await executor.execute(optimized_plan, ...)
# Expected: Faster execution (report already loaded)
```

### Step 7: Feedback

```python
feedback = LearningFeedback(
    execution_id="exec_124",
    user_id="user_123",
    success=True,
    reward=1.0,
    penalty=0.0,
    reason="execution_completed",
)
await learning.provide_feedback(feedback)
```

Pattern is reinforced:
```
Updated Pattern:
  - frequency: 2
  - success_count: 2
  - success_rate: 100%
  - confidence: 0.33 (2/6)
```

---

## Success Criteria

Phase 2.3 achieves success when:

✅ **Patterns emerge** from repeated behaviors
- After 5+ executions of same workflow, pattern appears

✅ **Predictions are accurate** (>80% confidence after learning)
- Forecasted next action matches actual ~80% of the time

✅ **Plans are optimized** based on learned patterns
- Tool ordering improves over time

✅ **Execution gets faster**
- Average duration decreases as patterns are learned

✅ **Feedback loop works**
- Reinforcement of successful patterns visible in metrics

✅ **Proactive behavior emerges**
- System suggests next actions before user asks

✅ **No manual tuning needed**
- Learning is fully automatic

---

## Memory Lifecycle

### Short-Term Memory (Session)
- **Storage**: Redis (fast, volatile)
- **Duration**: Session length
- **Content**: Last N executions
- **Purpose**: Immediate context, fast lookup

### Long-Term Memory (Historical)
- **Storage**: Database (persistent)
- **Duration**: Months/years
- **Content**: Compressed execution summaries
- **Purpose**: Pattern detection, trend analysis

### Pattern Layer
- **Storage**: Memory/Cache
- **Update**: Every N executions
- **Content**: Behavioral patterns with confidence
- **Purpose**: Drive predictions and optimizations

### Decay (Maintenance)
```python
# Weekly: Remove patterns not seen in 1 week (if low frequency)
await learning.decay_memory(user_id)
```

---

## Data Storage Strategy

### Redis (Short-Term)
```redis
{
  "user:user_123:short_term": [execution_trace_1, ...],
  "user:user_123:predictions": [prediction_1, ...],
}
```

### Database (Long-Term)
```sql
CREATE TABLE execution_traces (
  execution_id,
  user_id,
  goal,
  tool_sequence,
  outcome,
  duration_ms,
  timestamp,
);

CREATE TABLE behavioral_patterns (
  pattern_id,
  user_id,
  pattern,
  frequency,
  confidence,
  success_rate,
  avg_duration_ms,
);
```

### Cortex (Audit)
```
Every execution trace sent to Cortex:
  - Immutable audit trail
  - Authority verification
  - Compliance tracking
```

---

## Testing

### Test 1: Pattern Learning

```python
# User repeats: analyze → report (5 times)
for i in range(5):
    trace = ExecutionTrace(
        goal="Analyze",
        steps=[
            {"tool_id": "analyzer"},
            {"tool_id": "reporter"},
        ],
        outcome="success",
    )
    await learning.learn_from_trace(trace)

# Assert: Pattern exists with confidence > 0.7
patterns = learning.pattern_extractor.get_patterns_for_user(user_id)
assert len(patterns) >= 1
assert patterns[0].is_high_confidence()
```

### Test 2: Prediction

```python
# After learning, predict next action
prediction = await learning.make_prediction(user_id, "Analyze leads")

# Assert: Predicts "reporter"
assert prediction.next_action == "reporter"
assert prediction.confidence > 0.7
```

### Test 3: Optimization

```python
# Optimize plan for learned workflow
optimized = await learning.optimize_plan(
    user_id,
    "Analyze and report",
    current_plan,
)

# Assert: Reordered to match learned pattern
assert optimized[0]["tool_id"] == "analyzer"
assert optimized[1]["tool_id"] == "reporter"
```

### Test 4: Feedback

```python
# Provide success feedback
feedback = LearningFeedback(
    execution_id="exec_1",
    user_id=user_id,
    success=True,
    reward=1.0,
    penalty=0.0,
)
await learning.provide_feedback(feedback)

# Assert: Pattern success rate increases
pattern = patterns[0]
assert pattern.success_rate > 0.5
```

---

## Performance

### Expected Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Learn from trace | <10ms | Pattern extraction + memory update |
| Make prediction | <5ms | Pattern lookup + scoring |
| Optimize plan | <20ms | Pattern matching + reordering |
| Preload hints | <5ms | Tool extraction |

### Scalability

- **Per-user patterns**: ~100 (after weeks of use)
- **Pattern extraction**: O(1) per trace
- **Prediction**: O(n) where n = patterns (typically <100)
- **Memory per user**: ~100KB (short) + 1MB (long-term)

---

## Next Steps (Phase 2.4)

Current learning (Phase 2.3):
- ✅ Learns patterns from history
- ✅ Predicts next actions
- ✅ Optimizes plans

Future enhancements (Phase 2.4):
- → LLM-based reasoning for planning
- → Semantic understanding of goals
- → Multi-user pattern coordination
- → Anomaly detection (detect unusual requests)
- → Autonomous background execution

---

## Integration Checklist

- [ ] Memory module imported in main.py
- [ ] ExecutionTrace created after EHSA execution
- [ ] Learning system updated async
- [ ] Predictions used for preloading
- [ ] Plan optimization integrated
- [ ] Feedback signals connected
- [ ] Monitoring/dashboards configured
- [ ] Pattern decay job scheduled
- [ ] API endpoint: GET /api/memory/{user_id}/insights
- [ ] Examples run successfully
