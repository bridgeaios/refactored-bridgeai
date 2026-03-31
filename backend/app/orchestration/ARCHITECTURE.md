# EHSA Orchestrator — Phase 2.2: Orchestration Intelligence

## Overview

EHSA (Execution & Harmonization System Agent) transforms from a static executor into an **intelligent cognitive orchestrator**. The system now:

- **Thinks**: Decomposes goals into multi-step plans
- **Decides**: Selects appropriate tools based on context
- **Adapts**: Retries on failure, uses fallbacks, learns from outcomes
- **Traces**: Logs all decisions to Cortex for audit and learning

### Architecture

```
Input Goal
    ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: STRATEGIC PLANNING                             │
├─────────────────────────────────────────────────────────┤
│ Planner.generate_plan()                                 │
│   • Analyzes goal and context                           │
│   • Queries tool registry for available tools           │
│   • Creates multi-step execution plan                   │
│   • Returns: ExecutionPlan with steps                   │
└─────────────────────────────────────────────────────────┘
    ↓
ExecutionPlan (steps 1..N)
    ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 2: EXECUTION CONTROL LOOP                         │
├─────────────────────────────────────────────────────────┤
│ ExecutionLoop.execute()                                 │
│   for each step:                                        │
│     • Invoke tool via registry                          │
│     • Validate output                                   │
│     • Retry if validation fails (up to max_retries)    │
│     • Use fallback tool if available                    │
│     • Trace execution to Cortex                         │
│     • Update context for next step                      │
│   Returns: ExecutionResult with trace                   │
└─────────────────────────────────────────────────────────┘
    ↓
ExecutionResult
    ├─ status: "success" | "partial" | "failed"
    ├─ final_output: dict
    ├─ trace: [StepTrace, StepTrace, ...]
    └─ duration_ms: float
```

---

## Core Components

### 1. Tool Registry (`tool_registry.py`)

**Purpose**: Single source of truth for all available tools/services.

**Key Concepts**:
- **Tool**: Abstraction of a service function (crm.ingest_lead, analytics.summarize, etc.)
- **Tool Category**: Classification (analysis, transformation, communication, execution, validation, retrieval, persistence)
- **Tool Schema**: Input/output specification (required fields, types, etc.)
- **Authority Requirement**: Minimum authority level needed to invoke

**How it works**:
```python
# Register a tool
tool = Tool(
    id="crm.analyze_leads",
    name="Analyze Leads",
    category=ToolCategory.ANALYSIS,
    description="Analyze CRM leads for patterns",
    input_schema=ToolSchema(["data"], ["filters"], "dict"),
    output_schema=ToolSchema(["insights"], [], "dict"),
    authority_required="public",
    executor=analyze_leads_async_function,
)
get_registry().register(tool)

# Invoke a tool
result = await registry.invoke("crm.analyze_leads", {"data": leads})
```

**Authority-Based Access**:
```python
# Get tools available to authority level
public_tools = registry.list_by_authority("public")       # Fewer tools
orchestrator_tools = registry.list_by_authority("orchestrator")  # All tools
```

---

### 2. Planner (`planner.py`)

**Purpose**: Strategic planning — transforms goal into multi-step execution plan.

**Layer 1: Strategic Planning**

The planner uses **goal decomposition** to create a sequence of steps:

```python
# Input
goal = "Analyze data and generate insights"
context = {
    "input_data": {...},
    "user_preferences": {...},
    "past_decisions": [...]
}

# Process
plan = await planner.generate_plan(
    goal=goal,
    context=context,
    authority="economic"  # User authority level
)

# Output
ExecutionPlan:
  - goal: "Analyze data and generate insights"
  - steps:
    - Step 1: action="analyze", tool_id="analytics.summarize"
    - Step 2: action="transform", tool_id="analytics.report"
  - reasoning: "..."
```

**Plan Decomposition Strategy**:
- **Keywords**: Goal analyzed for keywords ("analyze", "transform", "generate", "create")
- **Tool Selection**: Matching tools retrieved from registry
- **Step Sequencing**: Steps ordered logically (analyze → transform → output)
- **Context Passing**: Each step receives relevant context from previous steps

**Future Enhancement** (optional): LLM-based planning
```python
# Use OpenAI/Claude to generate smarter plans
const plan = await openai.chat.completions.create({
    messages: [{role: "user", content: goal}],
    tools: available_tools,
    tool_choice: "auto"
})
```

---

### 3. Execution Loop (`execution_loop.py`)

**Purpose**: Control flow execution — runs plan with validation, retry, and tracing.

**Layer 2: Execution Control Loop**

For each step in the plan:

```python
for step in plan.steps:
    # Step 1: Invoke tool
    try:
        output = await registry.invoke(step.tool_id, step.input_params)
    except Exception:
        # Step 2: Retry (up to max_retries)
        if retries_left:
            continue  # Retry with same params
        elif step.fallback_tool_id:
            output = await registry.invoke(step.fallback_tool_id, ...)
        else:
            mark_as_failed()
            break  # Stop execution

    # Step 3: Validate output
    if not validate(output, step.validation_rule):
        if retries_left:
            continue  # Retry
        elif step.fallback_tool_id:
            # Try fallback
        else:
            mark_as_failed()

    # Step 4: Trace to Cortex
    trace.append({
        "step_id": step.step_id,
        "status": "success",
        "output": output,
        "duration_ms": ...,
    })

    # Step 5: Update context for next step
    context[f"step_{step.step_id}_output"] = output
```

**Validation Rules**:
- `"non_empty"`: Output must not be empty
- `"required_fields"`: Output must have expected fields
- `"schema"`: Output must match JSON schema (future)
- `None`: No validation, always pass

**Failure Handling**:
1. **Retry**: Try same tool again with same params (up to max_retries)
2. **Fallback**: Try alternative tool if specified
3. **Fail**: Mark step as failed if both attempts fail
4. **Trace**: Log all failures to Cortex

---

### 4. Orchestrator (`orchestrator.py`)

**Purpose**: Main service that ties all components together.

**Public API**:

```python
# Create orchestrator
ehsa = EHSA()

# Execute a goal
result = await ehsa.execute(
    goal="Analyze leads and generate report",
    twin_context={
        "input_data": leads,
        "user_preferences": {...},
        "past_decisions": [...]
    },
    authority="economic"  # User authority level
)

# Use result
print(result.status)           # "success" | "partial" | "failed"
print(result.final_output)     # Final step output
print(result.trace)            # All step traces
print(result.duration_ms)      # Total execution time
```

**Streaming Feedback** (for real-time UI updates):

```python
# Execute with step-by-step callbacks
async def on_step_complete(trace):
    print(f"Step {trace.step_id}: {trace.status.value}")

result = await ehsa.execute_with_feedback(
    goal="...",
    twin_context={...},
    authority="...",
    on_step_complete=on_step_complete,
)
```

---

### 5. Cortex Integration (`cortex_integration.py`)

**Purpose**: Authority enforcement, capability gating, unified audit trail.

**Authority-Based Access**:
```python
class AuthorityClass:
    PUBLIC = "public"              # Read-only, perception
    ECONOMIC = "economic"           # Marketplace, UBI, trade
    INTERNAL = "internal"          # State mutation
    ORCHESTRATOR = "orchestrator"   # System evolution
```

**Capability Gating**:
```python
# Check if capability is enabled before executing
if not capability_enabled("perception"):
    return {"error": "perception capability disabled"}

# Environment variable: BRIDGE_CAP_PERCEPTION=0 to disable
# Environment variable: BRIDGE_CAP_LOCK=1 to freeze at boot
```

**Unified Trace Emission**:
```python
# Traces automatically sent to Cortex
async def cortex_callback(trace_event):
    # trace_event = {
    #     "type": "orchestration_step",
    #     "execution_id": "abc123",
    #     "goal": "...",
    #     "authority": "internal",
    #     "step": {...},
    #     "timestamp": 1234567890.5
    # }

result = await ehsa.execute(
    goal="...",
    twin_context={...},
    authority="internal",
    cortex_callback=cortex_callback,
)
```

---

## Usage Patterns

### Pattern 1: Simple Single-Tool Execution

```python
result = await ehsa.execute(
    goal="Summarize the data",
    twin_context={"data": [...]},
    authority="public",
)
```

**What happens**:
1. Planner identifies "summarize" keyword
2. Selects best summary tool (e.g., "analytics.summarize")
3. Execution loop invokes tool
4. Validates output, traces result
5. Returns ExecutionResult

---

### Pattern 2: Complex Multi-Step Workflow

```python
result = await ehsa.execute(
    goal="Analyze leads, generate insights, create report, and send via email",
    twin_context={...},
    authority="economic",
)
```

**What happens**:
1. Planner decomposes into 4 steps:
   - Step 1: "analyze" → crm.analyze_leads
   - Step 2: "transform" → analytics.insights
   - Step 3: "generate" → analytics.report
   - Step 4: "communicate" → comms.email
2. Each step feeds into next (step 1 output → step 2 input)
3. If step fails, fallback tool tried (if available)
4. All steps traced to Cortex

---

### Pattern 3: Memory-Aware Decision Making

```python
twin_memory = {
    "cognitive_mode": "analytical",  # Influences tool selection
    "time_horizon": "short",         # Affects planning depth
    "preferences": {
        "detail_level": "high",
        "format": "structured",
    },
    "constraints": [
        "no_external_apis",
        "max_execution_time_ms=5000",
    ],
}

result = await ehsa.execute(
    goal="Generate report",
    twin_context=twin_memory,
    authority="economic",
)
```

**What happens**:
1. Planner uses twin memory to make decisions
2. Selects tools that respect constraints
3. Plans depth based on time_horizon
4. Output format matches preference
5. Decisions logged to Cortex for learning

---

## Success Criteria

Phase 2.2 is complete when:

✅ **Plans are dynamic** (not hardcoded)
✅ **Multiple tools used per request** (multi-step execution)
✅ **Execution adapts to results** (retry, fallback, validation)
✅ **Failures handled intelligently** (no silent failures)
✅ **Memory influences decisions** (twin context used in planning)
✅ **Authority enforced** (capability gating, scope restriction)
✅ **Traces sent to Cortex** (unified audit trail)
✅ **Test cases pass** (simple, complex, edge cases)

---

## Test Cases

### Test 1: Simple Single-Tool Execution

```python
goal = "Summarize this text"
# Expected: Single tool invoked, result returned
# Assertion: len(result.trace) == 1
```

### Test 2: Complex Multi-Step Execution

```python
goal = "Analyze data, generate insights, create report"
# Expected: 3+ steps executed in sequence
# Assertion: len(result.trace) >= 3, all successful
```

### Test 3: Error Handling and Retry

```python
# Tool fails on first attempt, succeeds on retry
goal = "Execute unreliable task"
# Expected: Step retried, then succeeds
# Assertion: trace[0].retry_count > 0, status == "success"
```

### Test 4: Fallback Mechanism

```python
# Primary tool fails, fallback succeeds
goal = "Task with fallback"
# Expected: Fallback tool invoked
# Assertion: trace[0].tool_id == fallback_tool_id, status == "fallback"
```

### Test 5: Authority Enforcement

```python
# PUBLIC user tries to execute ORCHESTRATOR-only goal
goal = "Evolve system"
authority = "public"
# Expected: Execution blocked
# Assertion: result.status == "failed", error mentions authority
```

### Test 6: Memory Influence

```python
# Twin memory with constraint affects planning
goal = "Generate report"
twin_context = {"constraints": ["max_duration_ms=1000"]}
# Expected: Planning respects constraint
# Assertion: result.duration_ms < 1000
```

---

## Integration Checklist

- [ ] Tool registry initialized with 20+ real services
- [ ] Planner tested on simple/complex/edge cases
- [ ] Execution loop tested with retry/fallback scenarios
- [ ] Authority enforcement validated
- [ ] Cortex trace integration tested
- [ ] Examples run successfully
- [ ] Documentation complete
- [ ] API endpoint added: `POST /api/orchestration/execute`
- [ ] Monitoring/observability configured

---

## Next Phase: Phase 2.3 — Memory Intelligence

EHSA Orchestrator (Phase 2.2) enables intelligent planning and execution.

Phase 2.3 will add **memory evolution**:
- Long-term learning (past decisions → future plans)
- Behavioral modeling (user patterns)
- Predictive personalization (anticipate needs)

The digital twin will learn from every execution trace.
