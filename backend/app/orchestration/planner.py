"""
EHSA Planner — Strategic Planning Engine (Two-Layer Model)

LAYER 1 — STRATEGIC PLANNING
  Input: goal + context + available_tools
  Output: step-by-step execution plan
  Decision: which tools, in what order

LAYER 2 — EXECUTION CONTROL LOOP
  Input: plan
  Output: validated result
  Control: retry, fallback, validation

Plan = list of Step objects, each specifying:
  - step_id: unique step identifier
  - action: high-level intent
  - tool_id: which tool to invoke
  - input_params: parameters for the tool
  - fallback_tool_id: alternative if primary fails
  - validation: how to validate the output
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from app.orchestration.tool_registry import ToolRegistry, get_registry


@dataclass
class ExecutionStep:
    """A single step in an execution plan."""
    step_id: int
    action: str  # High-level intent: "analyze", "transform", "validate", "communicate"
    tool_id: str  # Which tool to invoke
    input_params: dict[str, Any]  # Parameters for tool invocation
    fallback_tool_id: Optional[str] = None  # Alternative tool if primary fails
    validation_rule: Optional[str] = None  # How to validate: "required_fields", "non_empty", "schema"
    max_retries: int = 2  # Retry attempts before fallback


@dataclass
class ExecutionPlan:
    """Multi-step execution plan."""
    goal: str
    context: dict[str, Any]
    steps: list[ExecutionStep] = field(default_factory=list)
    reasoning: str = ""  # Why this plan was chosen

    def to_dict(self) -> dict[str, Any]:
        """Serialize plan to dict."""
        return {
            "goal": self.goal,
            "context": self.context,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "tool_id": s.tool_id,
                    "input_params": s.input_params,
                    "fallback_tool_id": s.fallback_tool_id,
                    "validation_rule": s.validation_rule,
                    "max_retries": s.max_retries,
                }
                for s in self.steps
            ],
            "reasoning": self.reasoning,
        }


class Planner:
    """
    Strategic planning engine for EHSA.

    Two-phase operation:
    1. Plan phase: Analyze goal and context, select tools, create execution steps
    2. Execution phase: Run steps with validation, retry, fallback
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or get_registry()

    async def generate_plan(
        self,
        goal: str,
        context: dict[str, Any],
        authority: str = "public",
    ) -> ExecutionPlan:
        """
        Generate an execution plan for the given goal.

        Args:
            goal: High-level goal/request
            context: Twin memory and decision context
            authority: User authority level (for tool filtering)

        Returns:
            ExecutionPlan with steps to achieve goal
        """
        # Get tools available to this authority
        available_tools = self.registry.list_by_authority(authority)

        # Build plan based on goal type and available tools
        plan = ExecutionPlan(
            goal=goal,
            context=context,
        )

        # Simple planning heuristic: goal → action → tool selection
        # This will be enhanced with LLM integration in future iterations
        steps = self._decompose_goal(goal, available_tools, context)
        plan.steps = steps
        plan.reasoning = f"Plan generated for goal: {goal}. {len(steps)} steps identified."

        return plan

    def _decompose_goal(
        self,
        goal: str,
        available_tools: list,
        context: dict[str, Any],
    ) -> list[ExecutionStep]:
        """
        Decompose goal into execution steps.

        This is a heuristic-based decomposition.
        Future: Replace with LLM-based reasoning.
        """
        steps: list[ExecutionStep] = []
        step_id = 1

        # Pattern matching on goal keywords
        goal_lower = goal.lower()

        # PATTERN 1: Summarize/analyze
        if any(kw in goal_lower for kw in ["summarize", "analyze", "analyze data", "insights"]):
            # Find analysis tools
            analysis_tools = [t for t in available_tools if "analyze" in t.id.lower()]
            if analysis_tools:
                primary = analysis_tools[0]
                steps.append(
                    ExecutionStep(
                        step_id=step_id,
                        action="analyze",
                        tool_id=primary.id,
                        input_params={"data": context.get("input_data", {})},
                        fallback_tool_id=None,
                        validation_rule="non_empty",
                    )
                )
                step_id += 1

        # PATTERN 2: Process/transform data
        elif any(kw in goal_lower for kw in ["transform", "process", "convert", "generate"]):
            transform_tools = [t for t in available_tools if "transform" in t.id.lower() or "process" in t.id.lower()]
            if transform_tools:
                primary = transform_tools[0]
                steps.append(
                    ExecutionStep(
                        step_id=step_id,
                        action="transform",
                        tool_id=primary.id,
                        input_params={"input": context.get("input_data", {})},
                        validation_rule="required_fields",
                    )
                )
                step_id += 1

        # PATTERN 3: Multi-step: analyze → transform → output
        elif any(kw in goal_lower for kw in ["analyze data", "generate", "create report", "insights"]):
            # Step 1: Analyze
            analysis_tools = [t for t in available_tools if "analyze" in t.id.lower()]
            if analysis_tools:
                steps.append(
                    ExecutionStep(
                        step_id=step_id,
                        action="analyze",
                        tool_id=analysis_tools[0].id,
                        input_params={"data": context.get("input_data", {})},
                    )
                )
                step_id += 1

            # Step 2: Transform
            transform_tools = [t for t in available_tools if "transform" in t.id.lower() or "generate" in t.id.lower()]
            if transform_tools:
                steps.append(
                    ExecutionStep(
                        step_id=step_id,
                        action="transform",
                        tool_id=transform_tools[0].id,
                        input_params={"analysis": "from_step_1"},  # Reference previous step
                        validation_rule="non_empty",
                    )
                )
                step_id += 1

            # Step 3: Output/render
            output_tools = [t for t in available_tools if "render" in t.id.lower() or "output" in t.id.lower()]
            if output_tools:
                steps.append(
                    ExecutionStep(
                        step_id=step_id,
                        action="output",
                        tool_id=output_tools[0].id,
                        input_params={"content": "from_step_2"},
                        validation_rule="required_fields",
                    )
                )

        # FALLBACK: If no patterns match, use first available tool
        if not steps and available_tools:
            tool = available_tools[0]
            steps.append(
                ExecutionStep(
                    step_id=1,
                    action="execute",
                    tool_id=tool.id,
                    input_params=context.get("input_data", {}),
                    validation_rule="non_empty",
                )
            )

        return steps
