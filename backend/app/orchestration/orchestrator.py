"""
EHSA Orchestrator — Main cognitive orchestration service.

Transforms:
  input (goal) → planning → execution → validated result

Integrates:
  - Planner: Strategic planning
  - ExecutionLoop: Control flow execution
  - ToolRegistry: Tool abstraction
  - Memory: Twin context and decision history
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from app.orchestration.execution_loop import ExecutionLoop, ExecutionResult
from app.orchestration.planner import ExecutionPlan, Planner
from app.orchestration.tool_registry import Tool, ToolRegistry, get_registry


class OrchestratorConfig:
    """Configuration for EHSA orchestrator."""

    def __init__(self):
        self.enable_memory_context = True  # Use twin memory in planning
        self.enable_tracing = True  # Trace execution
        self.enable_validation = True  # Validate outputs
        self.max_plan_depth = 10  # Max steps per plan


class EHSA:
    """
    EHSA — Cognitive Orchestrator Service

    The brain of BridgeAI. Transforms goals into intelligent, adaptive execution.

    Usage:
        ehsa = EHSA()
        result = await ehsa.execute(
            goal="Analyze data and generate insights",
            twin_context=twin.memory,
            authority="internal"
        )
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        config: Optional[OrchestratorConfig] = None,
    ):
        self.registry = registry or get_registry()
        self.config = config or OrchestratorConfig()
        self.planner = Planner(self.registry)
        self.executor = ExecutionLoop(self.registry)

    async def execute(
        self,
        goal: str,
        twin_context: Optional[dict[str, Any]] = None,
        authority: str = "public",
    ) -> ExecutionResult:
        """
        Execute a goal end-to-end.

        Args:
            goal: High-level goal/request
            twin_context: Digital twin memory and context
            authority: User authority level

        Returns:
            ExecutionResult with status, output, and trace
        """
        execution_id = str(uuid.uuid4())[:8]

        # PHASE 1: Strategic Planning
        context = twin_context or {}
        context["_goal"] = goal
        context["_execution_id"] = execution_id

        plan = await self.planner.generate_plan(
            goal=goal,
            context=context,
            authority=authority,
        )

        # PHASE 2: Execution Control Loop
        result = await self.executor.execute(
            plan=plan,
            plan_id=execution_id,
            authority=authority,
        )

        return result

    async def execute_with_feedback(
        self,
        goal: str,
        twin_context: Optional[dict[str, Any]] = None,
        authority: str = "public",
        on_step_complete: Optional[callable] = None,
    ) -> ExecutionResult:
        """
        Execute with step-by-step feedback callback.

        Useful for real-time UI updates or monitoring.

        Args:
            goal: High-level goal
            twin_context: Twin memory
            authority: Authority level
            on_step_complete: Callback(step_trace) after each step

        Returns:
            ExecutionResult
        """
        execution_id = str(uuid.uuid4())[:8]

        # Plan
        context = twin_context or {}
        context["_goal"] = goal
        context["_execution_id"] = execution_id

        plan = await self.planner.generate_plan(
            goal=goal,
            context=context,
            authority=authority,
        )

        # Execute with feedback
        result = ExecutionResult(
            plan_id=execution_id,
            goal=goal,
            status="success",
            total_steps=len(plan.steps),
        )

        execution_context = dict(context)

        for step in plan.steps:
            trace = await self.executor._execute_step(
                step=step,
                context=execution_context,
                authority=authority,
            )
            result.trace.append(trace)

            # Call feedback callback
            if on_step_complete:
                await on_step_complete(trace)

            # Update counters
            if trace.status.value in ("success", "fallback"):
                result.successful_steps += 1
            elif trace.status.value == "failed":
                result.failed_steps += 1
                result.status = "partial"

            # Update context
            if trace.output:
                execution_context[f"step_{step.step_id}_output"] = trace.output

        return result

    def register_tool(self, tool: Tool) -> None:
        """Register a new tool in the registry."""
        self.registry.register(tool)

    def list_tools(self, category: Optional[str] = None) -> list[dict]:
        """List available tools, optionally filtered by category."""
        tools = self.registry.all_tools()
        if category:
            tools = [t for t in tools if t.category.value == category]
        return [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category.value,
                "description": t.description,
                "authority_required": t.authority_required,
            }
            for t in tools
        ]
