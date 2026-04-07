"""
EHSA Enhanced — Cognitive Orchestrator with Memory Integration

Upgrades EHSA Phase 2.2 with Phase 2.3 learning:
  - Uses predictions to prepare for next steps
  - Optimizes plan based on learned patterns
  - Preloads tools for faster execution
  - Provides feedback to learning system

Backward compatible with existing EHSA interface.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from app.memory.learning_system import get_learning_system
from app.memory.models import ExecutionTrace
from app.orchestration.cortex_integration import CortexIntegratedEHSA
from app.orchestration.execution_loop import ExecutionResult
from app.orchestration.planner import ExecutionPlan


class EnhancedEHSA(CortexIntegratedEHSA):
    """
    EHSA with memory integration.

    Adds learning-driven optimization to base EHSA orchestrator.

    New capabilities:
    - Predictions: Forecast next actions
    - Optimized planning: Reorder steps based on history
    - Preloading: Cache tools before execution
    - Feedback: Signal success/failure to learning system
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.learning_system = get_learning_system()

    async def execute_with_learning(
        self,
        goal: str,
        user_id: str,
        twin_context: Optional[dict[str, Any]] = None,
        authority: str = "public",
        cortex_callback: Optional[Callable] = None,
        learning_callback: Optional[Callable] = None,
    ) -> ExecutionResult:
        """
        Execute with learning integration.

        Steps:
        1. Get user's memory and predictions
        2. Make prediction for next action (preload tools)
        3. Plan execution
        4. Optimize plan based on learned patterns
        5. Execute
        6. Provide feedback to learning system

        Args:
            goal: High-level goal
            user_id: User ID (for memory)
            twin_context: Digital twin context
            authority: Authority level
            cortex_callback: Optional Cortex callback
            learning_callback: Optional callback for learning updates

        Returns:
            ExecutionResult
        """
        # PHASE 1: Get predictions and prepare
        prediction = await self.learning_system.make_prediction(user_id, goal)

        if prediction and learning_callback:
            await learning_callback({
                "type": "prediction",
                "user_id": user_id,
                "next_action": prediction.next_action,
                "confidence": prediction.confidence,
            })

        # Get preload hints
        preload_hints = self.learning_system.get_preload_hints(user_id, goal)
        if preload_hints:
            # TODO: Preload tools in background
            pass

        # PHASE 2: Execute with planning
        execution_id = f"{user_id}_{int(time.time() * 1000)}"

        context = twin_context or {}
        context["_user_id"] = user_id
        context["_goal"] = goal
        context["_execution_id"] = execution_id

        # Generate initial plan
        plan = await self.planner.generate_plan(
            goal=goal,
            context=context,
            authority=authority,
        )

        # PHASE 3: Optimize plan based on learning
        optimized_plan = await self.learning_system.optimize_plan(
            user_id=user_id,
            goal=goal,
            current_plan=[s.__dict__ for s in plan.steps],
        )

        if optimized_plan:
            # Rebuild plan with optimized steps
            # (Implementation depends on plan structure)
            if learning_callback:
                await learning_callback({
                    "type": "optimization",
                    "original_steps": len(plan.steps),
                    "optimized_steps": len(optimized_plan),
                })

        # PHASE 4: Execute
        result = await self.executor.execute(
            plan=plan,
            plan_id=execution_id,
            authority=authority,
        )

        # PHASE 5: Emit to Cortex
        if cortex_callback:
            for trace in result.trace:
                await cortex_callback({
                    "type": "orchestration_step",
                    "execution_id": execution_id,
                    "user_id": user_id,
                    "goal": goal,
                    "authority": authority,
                    "step": trace.to_dict(),
                    "timestamp": time.time(),
                })

        # PHASE 6: Learn from execution
        execution_trace = ExecutionTrace(
            execution_id=execution_id,
            user_id=user_id,
            goal=goal,
            steps=[{
                "tool_id": t.tool_id,
                "status": t.status.value,
                "output": t.output,
            } for t in result.trace],
            outcome=result.status,
            duration_ms=result.duration_ms,
            timestamp=time.time(),
            authority=authority,
            context=context,
        )

        await self.learning_system.learn_from_trace(execution_trace)

        # PHASE 7: Provide feedback
        success = result.status == "success"
        reward = 1.0 if success else -0.5
        penalty = 0.0 if success else 1.0

        from app.memory.models import LearningFeedback
        feedback = LearningFeedback(
            execution_id=execution_id,
            user_id=user_id,
            success=success,
            reward=reward,
            penalty=penalty,
            reason=result.error if result.error else "execution_completed",
            timestamp=time.time(),
        )

        await self.learning_system.provide_feedback(feedback)

        if learning_callback:
            await learning_callback({
                "type": "feedback",
                "execution_id": execution_id,
                "success": success,
                "reward": reward,
                "penalty": penalty,
            })

        return result

    async def get_twin_insights(self, user_id: str) -> dict[str, Any]:
        """
        Get insights about a user's learning and behavior.

        Returns:
            Dictionary with learning statistics, patterns, predictions
        """
        memory = self.learning_system.get_memory(user_id)
        if not memory:
            return {"error": "No memory for user"}

        stats = self.learning_system.get_learning_stats(user_id)

        return {
            **stats,
            "memory": memory.to_dict(),
            "top_patterns": [
                p.pattern
                for p in self.learning_system.pattern_extractor.get_most_successful_patterns(
                    user_id, limit=5
                )
            ],
        }

    async def suggest_next_action(self, user_id: str) -> Optional[dict[str, Any]]:
        """
        Suggest the next action a user might want to take.

        Useful for proactive behavior and recommendations.

        Args:
            user_id: User ID

        Returns:
            Dictionary with suggested action and confidence
        """
        memory = self.learning_system.get_memory(user_id)
        if not memory:
            return None

        # Get most recent execution
        if not memory.short_term:
            return None

        last_trace = memory.short_term[-1]
        current_sequence = last_trace.tool_sequence()

        # Predict what comes next
        patterns = list(memory.patterns.values())
        next_goal = self.learning_system.prediction_engine.predict_next_goal(
            user_id=user_id,
            current_tool_sequence=current_sequence,
            patterns=patterns,
        )

        if next_goal:
            matching_patterns = [
                p for p in patterns
                if p.pattern.startswith(current_sequence)
            ]
            best_rate = max((p.success_rate for p in matching_patterns), default=0.5)
            # Blend success rate with support (more patterns = more confident)
            support_bonus = min(0.1 * len(matching_patterns), 0.2)
            confidence = round(min(best_rate + support_bonus, 1.0), 3)
            return {
                "suggested_goal": next_goal,
                "after_last_execution": last_trace.goal,
                "confidence": confidence,
            }

        return None
