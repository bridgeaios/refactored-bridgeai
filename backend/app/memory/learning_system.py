"""
Learning System — Core intelligence engine for Digital Twins

Responsibilities:
  1. Ingest execution traces from EHSA
  2. Extract behavioral patterns
  3. Make predictions for next actions
  4. Optimize execution plans based on learning
  5. Provide feedback signals for reinforcement
  6. Manage memory lifecycle (short-term → long-term)
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.memory.models import (
    DigitalTwinMemory,
    ExecutionTrace,
    LearningFeedback,
    OptimizationStrategy,
    Prediction,
)
from app.memory.pattern_extraction import PatternExtractor
from app.memory.prediction_engine import PredictionEngine


class LearningSystem:
    """
    Digital Twin Learning Engine.

    Transforms execution traces → patterns → predictions → optimizations.
    """

    def __init__(self, max_short_term: int = 20):
        """
        Initialize learning system.

        Args:
            max_short_term: Max traces to keep in short-term memory per twin
        """
        self.max_short_term = max_short_term
        self.memories: dict[str, DigitalTwinMemory] = {}
        self.pattern_extractor = PatternExtractor()
        self.prediction_engine = PredictionEngine()

    async def learn_from_trace(
        self,
        trace: ExecutionTrace,
    ) -> None:
        """
        Ingest a trace and update twin's learning.

        Called after every EHSA execution.

        Args:
            trace: ExecutionTrace from EHSA
        """
        user_id = trace.user_id

        # Get or create memory for this twin
        if user_id not in self.memories:
            self.memories[user_id] = DigitalTwinMemory(user_id=user_id)

        memory = self.memories[user_id]

        # Add to short-term memory
        memory.short_term.append(trace)

        # Keep short-term bounded
        if len(memory.short_term) > self.max_short_term:
            # Move oldest to long-term summary
            old_trace = memory.short_term.pop(0)
            memory.long_term.append(old_trace)

        # Extract patterns
        self.pattern_extractor.add_trace(user_id, trace)

        # Update statistics
        memory.total_executions += 1
        if trace.was_successful():
            memory.successful_executions += 1
        memory.last_updated = time.time()

        # Update patterns dictionary
        patterns = self.pattern_extractor.get_patterns_for_user(user_id, min_confidence=0.5)
        for pattern in patterns:
            memory.patterns[pattern.pattern_id] = pattern

    async def make_prediction(
        self,
        user_id: str,
        goal: str,
    ) -> Optional[Prediction]:
        """
        Predict the next action for a user given a goal.

        Args:
            user_id: User ID
            goal: Current goal/input

        Returns:
            Prediction with next_action and confidence, or None
        """
        # Get user's memory and patterns
        if user_id not in self.memories:
            return None

        memory = self.memories[user_id]
        patterns = list(memory.patterns.values())

        if not patterns:
            return None

        # Use prediction engine
        prediction = self.prediction_engine.predict_next_action(
            user_id=user_id,
            current_goal=goal,
            patterns=patterns,
        )

        # Store prediction in memory
        if prediction:
            memory.predictions.append(prediction)
            # Keep only recent predictions
            if len(memory.predictions) > 50:
                memory.predictions = memory.predictions[-50:]

        return prediction

    async def optimize_plan(
        self,
        user_id: str,
        goal: str,
        current_plan: list[dict],
    ) -> Optional[list[dict]]:
        """
        Optimize an execution plan based on learned patterns.

        Uses historical success rates to reorder tools.

        Args:
            user_id: User ID
            goal: Current goal
            current_plan: Initial plan from planner

        Returns:
            Optimized plan, or None if no optimization available
        """
        if user_id not in self.memories:
            return None

        memory = self.memories[user_id]
        patterns = list(memory.patterns.values())

        if not patterns:
            return None

        # Find patterns that match this goal
        matching = [
            p for p in patterns
            if self.prediction_engine._goal_matches_pattern(goal.lower(), p.pattern)
            and p.is_high_confidence()
        ]

        if not matching:
            return None

        # Get best pattern (highest success rate)
        best = max(matching, key=lambda p: p.success_rate)

        # Reorder plan based on successful sequence
        optimized = self._reorder_plan(current_plan, best.tool_sequence)

        # Store optimization strategy
        strategy_id = f"{user_id}:{goal}"
        memory.optimization[strategy_id] = OptimizationStrategy(
            user_id=user_id,
            goal_pattern=goal,
            preferred_tool_order=best.tool_sequence,
            preload_tools=best.tool_sequence[:3],
        )

        return optimized

    def _reorder_plan(
        self,
        plan: list[dict],
        preferred_order: list[str],
    ) -> list[dict]:
        """
        Reorder plan steps to match preferred tool order.

        Args:
            plan: Original plan
            preferred_order: Preferred tool sequence

        Returns:
            Reordered plan
        """
        if not plan or not preferred_order:
            return plan

        # Create mapping of tool_id to step
        tool_steps = {step.get("tool_id"): step for step in plan}

        # Build reordered plan
        reordered = []
        for tool_id in preferred_order:
            if tool_id in tool_steps:
                reordered.append(tool_steps[tool_id])

        # Add any steps not in preferred order
        for step in plan:
            if step.get("tool_id") not in preferred_order:
                reordered.append(step)

        return reordered

    async def provide_feedback(
        self,
        feedback: LearningFeedback,
    ) -> None:
        """
        Provide feedback signal for reinforcement learning.

        Used to strengthen/weaken patterns based on outcomes.

        Args:
            feedback: LearningFeedback with success/reward signals
        """
        user_id = feedback.user_id

        if user_id not in self.memories:
            return

        memory = self.memories[user_id]

        # Find the execution in short-term memory
        trace = None
        for t in memory.short_term:
            if t.execution_id == feedback.execution_id:
                trace = t
                break

        if not trace:
            return

        # Update success rates in patterns
        tool_sequence = trace.tool_sequence()
        patterns = self.pattern_extractor.get_patterns_for_user(user_id)

        for pattern in patterns:
            if pattern.pattern == tool_sequence:
                # Reinforce successful patterns
                if feedback.success:
                    pattern.success_count += int(feedback.reward)
                else:
                    pattern.failure_count += int(feedback.penalty)

                # Recalculate success rate
                total = pattern.success_count + pattern.failure_count
                pattern.success_rate = pattern.success_count / total if total > 0 else 0.0

    def get_memory(self, user_id: str) -> Optional[DigitalTwinMemory]:
        """
        Get memory for a user.

        Args:
            user_id: User ID

        Returns:
            DigitalTwinMemory or None
        """
        return self.memories.get(user_id)

    def get_learning_stats(self, user_id: str) -> dict[str, Any]:
        """
        Get learning statistics for a user.

        Returns:
            Dictionary with patterns, predictions, optimization info
        """
        memory = self.get_memory(user_id)
        if not memory:
            return {"error": "No memory for user"}

        patterns = self.pattern_extractor.get_pattern_stats(user_id)

        return {
            "user_id": user_id,
            "total_executions": memory.total_executions,
            "successful_executions": memory.successful_executions,
            "success_rate": (
                memory.successful_executions / memory.total_executions
                if memory.total_executions > 0
                else 0.0
            ),
            "learning_readiness": memory.learning_readiness(),
            "patterns": patterns,
            "active_predictions": len(memory.predictions),
            "optimization_strategies": len(memory.optimization),
            "last_updated": memory.last_updated,
        }

    def get_preload_hints(
        self,
        user_id: str,
        goal: str,
    ) -> list[str]:
        """
        Get tools to preload for a goal.

        Enables faster execution.

        Args:
            user_id: User ID
            goal: Current goal

        Returns:
            List of tool IDs to preload
        """
        memory = self.get_memory(user_id)
        if not memory:
            return []

        patterns = list(memory.patterns.values())
        return self.prediction_engine.get_preload_hints(user_id, goal, patterns)

    async def decay_memory(self, user_id: str) -> None:
        """
        Decay old patterns to prevent stale learning.

        Called periodically to remove patterns that haven't been seen recently.

        Args:
            user_id: User ID
        """
        memory = self.get_memory(user_id)
        if not memory:
            return

        current_time = time.time()
        one_week_ms = 7 * 24 * 60 * 60

        # Remove patterns older than 1 week with low frequency
        to_remove = []
        for pid, pattern in memory.patterns.items():
            age = current_time - pattern.last_seen
            if age > one_week_ms and pattern.frequency < 5:
                to_remove.append(pid)

        for pid in to_remove:
            del memory.patterns[pid]


# Global learning system instance
_LEARNING_SYSTEM: Optional[LearningSystem] = None


def get_learning_system() -> LearningSystem:
    """Get or create global learning system."""
    global _LEARNING_SYSTEM
    if _LEARNING_SYSTEM is None:
        _LEARNING_SYSTEM = LearningSystem()
    return _LEARNING_SYSTEM
