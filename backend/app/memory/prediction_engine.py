"""
Prediction Engine — Forecast likely next actions

Uses learned patterns to predict:
  - What tool/action comes next?
  - What's the likely next goal?
  - With what confidence?

Enables EHSA to preload tools and optimize execution.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.memory.models import BehavioralPattern, Prediction


class PredictionEngine:
    """
    Predict user actions based on learned patterns.

    Input: Current context (goal, tool sequence so far)
    Output: Prediction (next_action, confidence)
    """

    def __init__(self):
        self.predictions: dict[str, Prediction] = {}

    def predict_next_action(
        self,
        user_id: str,
        current_goal: str,
        patterns: list[BehavioralPattern],
    ) -> Optional[Prediction]:
        """
        Predict the next action given current goal and learned patterns.

        Algorithm:
        1. Find patterns that match current goal
        2. Identify most common next step
        3. Calculate confidence

        Args:
            user_id: User ID
            current_goal: Current goal/input
            patterns: List of learned patterns

        Returns:
            Prediction with next_action and confidence, or None if uncertain
        """
        if not patterns:
            return None

        # Find patterns that start with actions matching current goal keywords
        matching = self._find_matching_patterns(current_goal, patterns)
        if not matching:
            return None

        # Get the most likely next step
        next_action, confidence = self._extract_next_action(matching)
        if not next_action:
            return None

        # Create prediction
        prediction_id = f"{user_id}:{current_goal}:{next_action}"
        prediction = Prediction(
            prediction_id=prediction_id,
            user_id=user_id,
            context_pattern=current_goal,
            next_action=next_action,
            next_goal=self._infer_goal(next_action),
            confidence=confidence,
            based_on_pattern=matching[0].pattern_id if matching else "unknown",
            timestamp=time.time(),
        )

        return prediction

    def _find_matching_patterns(
        self,
        goal: str,
        patterns: list[BehavioralPattern],
    ) -> list[BehavioralPattern]:
        """
        Find patterns that likely apply to current goal.

        Matching strategy:
        - Goal contains keywords from pattern's context
        - Pattern has high success rate
        - Pattern is recent (within last week)
        """
        goal_lower = goal.lower()

        matching = []
        for pattern in patterns:
            # Simple keyword matching
            # (Future: Use ML for better semantic matching)
            if self._goal_matches_pattern(goal_lower, pattern.pattern):
                matching.append(pattern)

        # Sort by success rate (highest first)
        return sorted(matching, key=lambda p: p.success_rate, reverse=True)

    def _goal_matches_pattern(self, goal: str, pattern: str) -> bool:
        """
        Simple heuristic: Does goal match pattern?

        Example:
        - Goal: "analyze leads"
        - Pattern: "analyzer → reporter"
        - Match: Yes (analyzer in pattern, analyze in goal)
        """
        pattern_lower = pattern.lower()

        # Check if goal contains any tool from pattern
        pattern_tools = pattern_lower.split(" → ")
        for tool in pattern_tools:
            # Simple substring matching
            if tool.split(".")[0] in goal:  # "crm" from "crm.analyze_leads"
                return True

        return False

    def _extract_next_action(
        self,
        patterns: list[BehavioralPattern],
    ) -> tuple[Optional[str], float]:
        """
        Extract the most likely next action from matching patterns.

        Algorithm:
        1. Get first tool from each pattern's sequence
        2. Weight by pattern confidence
        3. Return most likely

        Returns:
            (next_action, confidence) or (None, 0.0)
        """
        if not patterns:
            return None, 0.0

        # Weight actions by pattern confidence
        action_weights = {}
        for pattern in patterns:
            if pattern.tool_sequence:
                first_tool = pattern.tool_sequence[0]
                weight = pattern.confidence * pattern.success_rate
                action_weights[first_tool] = action_weights.get(first_tool, 0) + weight

        if not action_weights:
            return None, 0.0

        # Get highest weighted action
        next_action = max(action_weights, key=action_weights.get)
        confidence = min(action_weights[next_action], 1.0)

        return next_action, confidence

    def _infer_goal(self, action: str) -> Optional[str]:
        """
        Infer likely goal from action.

        Simple mapping based on tool names.
        Future: Use more sophisticated inference.
        """
        action_lower = action.lower()

        # Simple heuristics
        if "analyze" in action_lower:
            return "Analyze data"
        elif "report" in action_lower or "generate" in action_lower:
            return "Generate report"
        elif "email" in action_lower or "send" in action_lower:
            return "Send notification"
        elif "summary" in action_lower or "summarize" in action_lower:
            return "Summarize"

        return None

    def predict_next_goal(
        self,
        user_id: str,
        current_tool_sequence: str,
        patterns: list[BehavioralPattern],
    ) -> Optional[str]:
        """
        Predict the next goal/request after current sequence.

        Useful for proactive behavior.

        Args:
            user_id: User ID
            current_tool_sequence: What tools were just used
            patterns: Learned patterns

        Returns:
            Likely next goal, or None
        """
        # Find patterns that start with current sequence
        matching = [
            p for p in patterns
            if p.pattern.startswith(current_tool_sequence)
        ]

        if not matching:
            return None

        # Look at what comes after in those patterns
        for pattern in sorted(matching, key=lambda p: p.success_rate, reverse=True):
            # Extract what comes after current sequence
            remaining = pattern.pattern.replace(current_tool_sequence, "").strip(" → ")
            if remaining:
                return self._infer_goal(remaining.split(" → ")[0])

        return None

    def get_preload_hints(
        self,
        user_id: str,
        current_goal: str,
        patterns: list[BehavioralPattern],
    ) -> list[str]:
        """
        Get list of tools that should be preloaded for this goal.

        Preloading tools before execution reduces latency.

        Args:
            user_id: User ID
            current_goal: Current goal
            patterns: Learned patterns

        Returns:
            List of tool IDs to preload
        """
        matching = self._find_matching_patterns(current_goal, patterns)
        if not matching:
            return []

        # Get tool sequence from best matching pattern
        best = matching[0]
        return best.tool_sequence[:3]  # Preload first 3 tools

    def evaluate_prediction_accuracy(
        self,
        prediction: Prediction,
        actual_next_action: str,
    ) -> float:
        """
        Evaluate if prediction was correct.

        Returns:
            Accuracy score (0-1)
        """
        if prediction.next_action == actual_next_action:
            return 1.0
        return 0.0
