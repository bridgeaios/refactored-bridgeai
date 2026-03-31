"""
EHSA Orchestrator Usage Examples

Demonstrates:
  1. Simple goal execution
  2. Complex multi-step planning
  3. Memory-aware execution
  4. Error handling and retry
  5. Cortex integration
"""
from __future__ import annotations

from app.orchestration.cortex_integration import CortexIntegratedEHSA
from app.orchestration.orchestrator import OrchestratorConfig, EHSA
from app.orchestration.tool_builders import (
    register_analytics_tools,
    register_communication_tools,
    register_crm_tools,
)


# =============================================================================
# Example 1: Simple Goal Execution
# =============================================================================


async def example_simple_goal():
    """Simple: Execute a single-step goal."""
    # Initialize EHSA with config
    config = OrchestratorConfig()
    config.enable_tracing = True

    ehsa = EHSA(config=config)

    # Register some tools
    register_crm_tools()
    register_analytics_tools()

    # Execute a simple goal
    result = await ehsa.execute(
        goal="Summarize the data",
        twin_context={"input_data": {"leads": [1, 2, 3]}},
        authority="public",
    )

    # Check results
    print(f"Status: {result.status}")
    print(f"Steps executed: {result.successful_steps}/{result.total_steps}")
    print(f"Output: {result.final_output}")
    print(f"Trace: {[t.tool_id for t in result.trace]}")

    return result


# =============================================================================
# Example 2: Complex Multi-Step Planning
# =============================================================================


async def example_multi_step_planning():
    """Complex: Multi-step workflow with analysis → transformation → output."""
    ehsa = EHSA()

    # Register tools
    register_crm_tools()
    register_analytics_tools()
    register_communication_tools()

    # Execute a complex goal
    result = await ehsa.execute(
        goal="Analyze data, generate insights, and create report",
        twin_context={
            "input_data": {"leads": [1, 2, 3, 4, 5]},
            "user_id": "user_123",
        },
        authority="economic",
    )

    print(f"\nMulti-step execution:")
    print(f"Plan steps: {result.total_steps}")
    print(f"Successful: {result.successful_steps}")
    print(f"Failed: {result.failed_steps}")
    print(f"Total duration: {result.duration_ms:.2f}ms")

    for trace in result.trace:
        print(f"  Step {trace.step_id}: {trace.action} via {trace.tool_id} → {trace.status.value}")

    return result


# =============================================================================
# Example 3: Memory-Aware Execution
# =============================================================================


async def example_memory_aware():
    """
    Memory-aware: Use digital twin context to influence planning.

    The planner uses twin memory (preferences, past decisions, constraints)
    to make smarter tool selections.
    """
    ehsa = EHSA()
    register_analytics_tools()

    # Digital twin context (from cognitive_twin.py)
    twin_memory = {
        "user_id": "user_456",
        "cognitive_mode": "analytical",  # Influences tool selection
        "time_horizon": "short",  # Affects planning depth
        "preferences": {
            "detail_level": "high",
            "format": "structured",
        },
        "past_decisions": [
            {"goal": "analyze", "tool_used": "analytics.summarize"},
            {"goal": "report", "tool_used": "analytics.report"},
        ],
        "constraints": [
            "no_external_apis",
            "max_execution_time_ms=5000",
        ],
    }

    result = await ehsa.execute(
        goal="Generate report from data",
        twin_context=twin_memory,
        authority="economic",
    )

    print(f"\nMemory-aware execution:")
    print(f"Twin mode influenced planning: {result.plan_id}")

    return result


# =============================================================================
# Example 4: Streaming Feedback
# =============================================================================


async def example_streaming_feedback():
    """
    Streaming feedback: Real-time step-by-step callbacks.

    Useful for UI updates, monitoring, and step-level error handling.
    """
    ehsa = EHSA()
    register_analytics_tools()

    executed_steps = []

    async def on_step_complete(trace):
        """Called after each step completes."""
        executed_steps.append({
            "step": trace.step_id,
            "status": trace.status.value,
            "duration_ms": trace.duration_ms,
        })
        print(f"Step {trace.step_id} completed: {trace.status.value} ({trace.duration_ms:.0f}ms)")

    result = await ehsa.execute_with_feedback(
        goal="Analyze and summarize data",
        twin_context={"input_data": {}},
        authority="public",
        on_step_complete=on_step_complete,
    )

    print(f"\nStreaming execution completed: {result.status}")
    print(f"Steps executed: {len(executed_steps)}")

    return result


# =============================================================================
# Example 5: Cortex-Integrated Execution
# =============================================================================


async def example_cortex_integration():
    """
    Cortex integration: Authority-enforced execution with audit trail.

    Demonstrates:
    - Authority validation (prevents unauthorized tool access)
    - Capability gating (evolution, perception, trade, etc.)
    - Unified trace emission to Cortex
    """
    ehsa = CortexIntegratedEHSA()
    register_crm_tools()

    traces_to_cortex = []

    async def cortex_callback(trace_event):
        """Send trace to Cortex audit system."""
        traces_to_cortex.append(trace_event)
        print(f"Cortex received: {trace_event['type']} from {trace_event['authority']}")

    # Execute with ORCHESTRATOR authority
    result = await ehsa.execute(
        goal="Analyze leads",
        twin_context={"input_data": {"leads": [1, 2, 3]}},
        authority="orchestrator",  # ORCHESTRATOR has full scope
        cortex_callback=cortex_callback,
    )

    print(f"\nCortex integration:")
    print(f"Authority used: orchestrator")
    print(f"Traces sent to Cortex: {len(traces_to_cortex)}")

    # Show what tools are available to different authorities
    print(f"\nTools available to 'public': {len(ehsa.get_scoped_tools('public'))}")
    print(f"Tools available to 'economic': {len(ehsa.get_scoped_tools('economic'))}")
    print(f"Tools available to 'internal': {len(ehsa.get_scoped_tools('internal'))}")
    print(f"Tools available to 'orchestrator': {len(ehsa.get_scoped_tools('orchestrator'))}")

    return result


# =============================================================================
# Example 6: Error Handling and Retry
# =============================================================================


async def example_error_handling():
    """
    Error handling: Demonstrate retry and fallback mechanisms.

    When a tool fails:
    1. Retry with same parameters (up to max_retries)
    2. Try fallback tool if available
    3. Mark step as failed if both fail
    """
    # Create EHSA and register tools
    ehsa = EHSA()

    # Tool that fails on first attempt, then succeeds
    attempt_count = 0

    async def unreliable_tool(data: dict, **kwargs) -> dict:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise Exception("First attempt failed (simulated)")
        return {"output": {"data": "Success on retry"}}

    # Register the unreliable tool
    from app.orchestration.tool_registry import Tool, ToolCategory, ToolSchema

    tool = Tool(
        id="test.unreliable",
        name="Unreliable Tool",
        category=ToolCategory.ANALYSIS,
        description="Tool that fails on first attempt",
        input_schema=ToolSchema(["data"], [], "dict"),
        output_schema=ToolSchema(["output"], [], "dict"),
        authority_required="public",
        executor=unreliable_tool,
    )

    ehsa.register_tool(tool)

    # Execute and let the retry mechanism handle the failure
    result = await ehsa.execute(
        goal="Execute unreliable task",
        twin_context={"data": "test"},
        authority="public",
    )

    print(f"\nError handling test:")
    print(f"Result status: {result.status}")
    print(f"Retries used: {result.trace[0].retry_count if result.trace else 0}")

    return result


# =============================================================================
# Main: Run all examples
# =============================================================================


async def run_all_examples():
    """Run all examples."""
    print("=" * 80)
    print("EHSA Orchestrator Examples")
    print("=" * 80)

    print("\n[1] Simple Goal Execution")
    print("-" * 80)
    await example_simple_goal()

    print("\n[2] Multi-Step Planning")
    print("-" * 80)
    await example_multi_step_planning()

    print("\n[3] Memory-Aware Execution")
    print("-" * 80)
    await example_memory_aware()

    print("\n[4] Streaming Feedback")
    print("-" * 80)
    await example_streaming_feedback()

    print("\n[5] Cortex Integration")
    print("-" * 80)
    await example_cortex_integration()

    print("\n[6] Error Handling and Retry")
    print("-" * 80)
    await example_error_handling()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all_examples())
