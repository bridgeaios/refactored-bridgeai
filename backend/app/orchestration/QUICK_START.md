# EHSA Orchestrator — Quick Start Guide

## Installation & Setup

```python
# 1. Import
from app.orchestration.orchestrator import EHSA
from app.orchestration.tool_builders import (
    register_crm_tools,
    register_analytics_tools,
)

# 2. Initialize
ehsa = EHSA()

# 3. Register tools
register_crm_tools()
register_analytics_tools()

# 4. Execute
result = await ehsa.execute(
    goal="Analyze leads",
    twin_context={},
    authority="public"
)
```

---

## Basic Usage

### Execute a Goal

```python
result = await ehsa.execute(
    goal="Summarize the data",
    twin_context={"data": [...]},
    authority="public"
)

print(f"Status: {result.status}")          # "success", "partial", "failed"
print(f"Output: {result.final_output}")    # dict
print(f"Duration: {result.duration_ms}ms") # float
```

---

## Advanced Usage

### Multi-Step Workflow with Feedback

```python
async def on_step_done(trace):
    print(f"Step {trace.step_id}: {trace.status.value}")

result = await ehsa.execute_with_feedback(
    goal="Analyze, transform, output",
    twin_context={...},
    authority="economic",
    on_step_complete=on_step_done,
)
```

---

### Cortex Integration

```python
from app.orchestration.cortex_integration import CortexIntegratedEHSA

ehsa = CortexIntegratedEHSA()

async def to_cortex(trace_event):
    print(f"Cortex: {trace_event['type']}")

result = await ehsa.execute(
    goal="Evolve system",
    twin_context={...},
    authority="orchestrator",
    cortex_callback=to_cortex,
)
```

---

## Registering Custom Tools

```python
from app.orchestration.tool_builders import build_analysis_tool
from app.orchestration.tool_registry import register_tool

# 1. Create async executor
async def my_analyzer(data: dict, **kwargs) -> dict:
    # Your logic
    return {"output": {"insights": [...]}}

# 2. Build tool
tool = build_analysis_tool(
    tool_id="custom.analyzer",
    name="My Analyzer",
    description="Custom analysis tool",
    service_executor=my_analyzer,
    authority_required="public",
)

# 3. Register
register_tool(tool)

# 4. Use
result = await ehsa.execute(
    goal="Analyze with custom tool",
    twin_context={...},
    authority="public",
)
```

---

## Checking Available Tools

```python
# List all tools
all_tools = ehsa.list_tools()

# List by category
analysis_tools = ehsa.list_tools(category="analysis")

# List by authority (Cortex-integrated only)
public_tools = ehsa.get_scoped_tools("public")
orchestrator_tools = ehsa.get_scoped_tools("orchestrator")
```

---

## Understanding Results

```python
result = ExecutionResult:
  - plan_id: str                # Unique execution ID
  - goal: str                   # Original goal
  - status: str                 # "success" | "partial" | "failed"
  - final_output: dict          # Last step output
  - error: str | None           # If failed
  - trace: [StepTrace, ...]     # All steps
  - total_steps: int
  - successful_steps: int
  - failed_steps: int
  - duration_ms: float

# Access traces
for trace in result.trace:
    print(f"Step {trace.step_id}")
    print(f"  Action: {trace.action}")
    print(f"  Tool: {trace.tool_id}")
    print(f"  Status: {trace.status}")
    print(f"  Output: {trace.output}")
    print(f"  Error: {trace.error}")
    print(f"  Duration: {trace.duration_ms}ms")
    print(f"  Retries: {trace.retry_count}")
```

---

## Error Handling

```python
result = await ehsa.execute(goal="...", ...)

if result.status == "failed":
    print(f"Error: {result.error}")
    # Handle failure
elif result.status == "partial":
    print(f"Partial success: {result.successful_steps}/{result.total_steps}")
    # Handle partial (some steps failed)
else:
    print(f"Success: {result.final_output}")
    # Use output
```

---

## Common Patterns

### Pattern: Analyze → Generate Report

```python
goal = "Analyze leads and generate report"
result = await ehsa.execute(goal, {...}, "economic")

# Steps automatically created:
# 1. analytics.analyze → insight extraction
# 2. analytics.report → report generation
# 3. Result ready
```

### Pattern: Memory-Influenced Planning

```python
result = await ehsa.execute(
    goal="Process request",
    twin_context={
        "cognitive_mode": "analytical",
        "preferences": {"detail_level": "high"},
        "constraints": ["max_duration_ms=5000"],
    },
    authority="economic",
)
```

### Pattern: Real-Time Monitoring

```python
steps = []

async def track(trace):
    steps.append({
        "step": trace.step_id,
        "status": trace.status.value,
        "duration": trace.duration_ms,
    })
    # Send to WebSocket, UI, etc.

result = await ehsa.execute_with_feedback(
    goal="...",
    twin_context={...},
    authority="...",
    on_step_complete=track,
)
```

---

## Configuration

```python
from app.orchestration.orchestrator import OrchestratorConfig

config = OrchestratorConfig()
config.enable_memory_context = True      # Use twin memory
config.enable_tracing = True             # Log all steps
config.enable_validation = True          # Validate outputs
config.max_plan_depth = 10               # Max steps per plan

ehsa = EHSA(config=config)
```

---

## Authority Levels

```
PUBLIC         → read, perception, speech
ECONOMIC       → + marketplace, ubi, trade
INTERNAL       → + state_mutation
ORCHESTRATOR   → + evolution, system
```

Lower authority levels inherit all permissions from levels below them.

---

## Tools Categories

```
ANALYSIS       → Analyze data, extract insights
TRANSFORMATION → Process, transform, convert data
COMMUNICATION  → Email, notifications, messages
EXECUTION      → Business logic, state changes
VALIDATION     → Verify, check, validate data
RETRIEVAL      → Fetch, read, query data
PERSISTENCE    → Store, write, persist data
```

---

## Troubleshooting

**Q: My tool isn't being invoked**
A: Check:
- Tool is registered in registry
- Goal keywords match tool name
- Authority level is sufficient
- Capability flags are enabled

**Q: Steps are failing silently**
A: Check:
- Validation rules (non_empty, required_fields)
- Fallback tool is available
- Error logs in traces

**Q: Planning doesn't match my goal**
A: Current planner uses keyword matching. For complex goals:
- Use simpler, more specific goal wording
- Or implement LLM-based planning (Phase 2.3)

**Q: Memory isn't influencing planning**
A: Memory-aware planning requires:
- Proper twin_context format
- Planner enhancement (planned for Phase 2.3)
- Currently uses heuristics only

---

## Next Steps

1. Register your services as tools (tool_builders.py)
2. Test with examples.py
3. Add API endpoint: POST /api/orchestration/execute
4. Monitor traces in Cortex dashboard
5. Phase 2.3: Memory evolution and learning
