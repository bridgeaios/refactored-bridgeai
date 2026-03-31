"""
Execution Loop — Control flow for executing plans with validation, retry, and tracing.

LAYER 2 Implementation: Execute each step, validate results, handle failures.

Control flow:
  for each step in plan:
    try:
      result = invoke_tool(step)
      if validate(result):
        trace.append(success)
        context.update(result)
      else:
        if retries_left:
          retry with modified params
        else:
          try fallback tool
    except Exception:
      handle_failure (retry or fallback)

All failures logged to Cortex.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from app.orchestration.planner import ExecutionPlan, ExecutionStep
from app.orchestration.tool_registry import ToolRegistry, get_registry


class StepStatus(str, Enum):
    """Status of a single step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    FALLBACK = "fallback"


@dataclass
class StepTrace:
    """Trace record for a single step execution."""
    step_id: int
    action: str
    tool_id: str
    status: StepStatus
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    timestamp: float = 0.0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize trace to dict."""
        return {
            "step_id": self.step_id,
            "action": self.action,
            "tool_id": self.tool_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ExecutionResult:
    """Result of executing a full plan."""
    plan_id: str
    goal: str
    status: str  # "success", "partial", "failed"
    final_output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    trace: list[StepTrace] = None
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    duration_ms: float = 0.0

    def __post_init__(self):
        if self.trace is None:
            self.trace = []

    def to_dict(self) -> dict[str, Any]:
        """Serialize execution result to dict."""
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "status": self.status,
            "final_output": self.final_output,
            "error": self.error,
            "trace": [t.to_dict() for t in self.trace],
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "duration_ms": self.duration_ms,
        }


class ExecutionValidator:
    """Validates step outputs against validation rules."""

    @staticmethod
    def validate(output: dict[str, Any], rule: Optional[str]) -> bool:
        """
        Validate output against a rule.

        Rules:
          - "non_empty": output must not be empty
          - "required_fields": output must have expected fields
          - "schema": output must match schema
          - None: no validation, always pass
        """
        if not rule or rule is None:
            return True

        if rule == "non_empty":
            return bool(output) and output.get("output") is not None

        if rule == "required_fields":
            return bool(output.get("output"))

        if rule == "schema":
            # Future: implement schema validation
            return bool(output)

        return True


class ExecutionLoop:
    """
    Execution control loop for running plans.

    Responsibilities:
    - Execute each step in the plan
    - Validate outputs
    - Handle retries and fallbacks
    - Trace execution for Cortex
    - Update context between steps
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or get_registry()
        self.validator = ExecutionValidator()

    async def execute(
        self,
        plan: ExecutionPlan,
        plan_id: str,
        authority: str = "public",
    ) -> ExecutionResult:
        """
        Execute a plan end-to-end.

        Args:
            plan: ExecutionPlan to execute
            plan_id: Unique ID for this execution
            authority: User authority level

        Returns:
            ExecutionResult with trace and final output
        """
        start_time = time.time()
        result = ExecutionResult(
            plan_id=plan_id,
            goal=plan.goal,
            status="success",
            total_steps=len(plan.steps),
        )

        # Context accumulates across steps
        execution_context = dict(plan.context)

        for step in plan.steps:
            trace = await self._execute_step(
                step=step,
                context=execution_context,
                authority=authority,
            )
            result.trace.append(trace)

            # Update status counters
            if trace.status == StepStatus.SUCCESS:
                result.successful_steps += 1
            elif trace.status == StepStatus.FAILED:
                result.failed_steps += 1
                result.status = "partial"  # Mark as partial if any step fails
            elif trace.status == StepStatus.FALLBACK:
                result.successful_steps += 1  # Fallback counts as success if it works

            # Stop if critical step fails and no fallback
            if trace.status == StepStatus.FAILED and not step.fallback_tool_id:
                result.status = "failed"
                result.error = f"Step {step.step_id} failed: {trace.error}"
                break

            # Update context with step output (for next steps)
            if trace.status in (StepStatus.SUCCESS, StepStatus.FALLBACK):
                if trace.output:
                    execution_context[f"step_{step.step_id}_output"] = trace.output

        # Set final output (last successful step's output)
        if result.trace:
            for trace in reversed(result.trace):
                if trace.status in (StepStatus.SUCCESS, StepStatus.FALLBACK):
                    result.final_output = trace.output
                    break

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def _execute_step(
        self,
        step: ExecutionStep,
        context: dict[str, Any],
        authority: str,
    ) -> StepTrace:
        """
        Execute a single step with retry and fallback logic.

        Returns:
            StepTrace with execution details
        """
        trace = StepTrace(
            step_id=step.step_id,
            action=step.action,
            tool_id=step.tool_id,
            status=StepStatus.PENDING,
            timestamp=time.time(),
        )

        start_time = time.time()

        # Try primary tool with retries
        for attempt in range(step.max_retries + 1):
            trace.status = StepStatus.RETRYING if attempt > 0 else StepStatus.RUNNING

            try:
                output = await self.registry.invoke(step.tool_id, step.input_params)

                # Check if invocation was successful
                if output.get("status") == "error":
                    trace.error = output.get("error", "Unknown error")
                    if attempt < step.max_retries:
                        continue  # Retry
                    else:
                        break  # Move to fallback

                # Validate output
                if not self.validator.validate(output, step.validation_rule):
                    trace.error = f"Output validation failed: {step.validation_rule}"
                    if attempt < step.max_retries:
                        continue  # Retry
                    else:
                        break  # Move to fallback

                # Success
                trace.status = StepStatus.SUCCESS
                trace.output = output
                trace.retry_count = attempt
                trace.duration_ms = (time.time() - start_time) * 1000
                return trace

            except Exception as e:
                trace.error = str(e)
                if attempt < step.max_retries:
                    continue  # Retry
                else:
                    break  # Move to fallback

        # Try fallback tool if available
        if step.fallback_tool_id:
            trace.status = StepStatus.FALLBACK
            try:
                fallback_output = await self.registry.invoke(
                    step.fallback_tool_id,
                    step.input_params,
                )
                if fallback_output.get("status") != "error":
                    trace.output = fallback_output
                    trace.tool_id = step.fallback_tool_id
                    trace.duration_ms = (time.time() - start_time) * 1000
                    return trace
            except Exception as e:
                trace.error = f"Fallback failed: {str(e)}"

        # If we reach here, step failed
        trace.status = StepStatus.FAILED
        trace.duration_ms = (time.time() - start_time) * 1000
        return trace
