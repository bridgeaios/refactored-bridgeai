"""
Pattern Extraction Engine — Derive behavioral insights from execution history

Process:
  1. Ingest execution traces
  2. Identify tool sequences
  3. Calculate frequency and confidence
  4. Track success rates
  5. Store high-confidence patterns

Patterns emerge from repeated behaviors and successful outcomes.
"""
from __future__ import annotations

import time
from collections import Counter
from typing import Any

from app.memory.models import BehavioralPattern, ExecutionTrace


class PatternExtractor:
    """
    Extract behavioral patterns from execution traces.

    Patterns capture: "User repeatedly does X → Y → Z, with 85% success rate"
    """

    def __init__(self):
        self.patterns: dict[str, BehavioralPattern] = {}

    def add_trace(
        self,
        user_id: str,
        trace: ExecutionTrace,
    ) -> None:
        """
        Process a single execution trace and update patterns.

        Args:
            user_id: User ID
            trace: ExecutionTrace from EHSA execution
        """
        # Extract tool sequence
        tool_sequence = trace.tool_sequence()
        if not tool_sequence or tool_sequence == "unknown":
            return  # Skip empty sequences

        # Get or create pattern
        pattern_id = f"{user_id}:{tool_sequence}"
        if pattern_id not in self.patterns:
            self.patterns[pattern_id] = BehavioralPattern(
                pattern_id=pattern_id,
                user_id=user_id,
                pattern=tool_sequence,
                frequency=0,
                confidence=0.0,
                last_seen=time.time(),
                success_rate=0.0,
                avg_duration_ms=0.0,
                tool_sequence=tool_sequence.split(" → "),
            )

        pattern = self.patterns[pattern_id]

        # Update frequency
        pattern.frequency += 1
        pattern.last_seen = time.time()

        # Update success tracking
        if trace.was_successful():
            pattern.success_count += 1
        else:
            pattern.failure_count += 1

        # Calculate metrics
        total = pattern.success_count + pattern.failure_count
        pattern.success_rate = pattern.success_count / total if total > 0 else 0.0

        # Calculate confidence (need multiple observations)
        # Confidence grows with frequency: 1 observation = 0.2, 5 observations = 0.8
        pattern.confidence = min(pattern.frequency / 6.0, 1.0)

        # Update duration (running average)
        old_avg = pattern.avg_duration_ms
        pattern.avg_duration_ms = (
            (old_avg * (pattern.frequency - 1) + trace.duration_ms) / pattern.frequency
        )

    def extract_high_confidence_patterns(self) -> dict[str, BehavioralPattern]:
        """
        Get patterns with high confidence.

        Threshold: confidence > 0.7 AND frequency >= 5
        """
        return {
            pid: p
            for pid, p in self.patterns.items()
            if p.is_high_confidence()
        }

    def get_patterns_for_user(
        self,
        user_id: str,
        min_confidence: float = 0.7,
    ) -> list[BehavioralPattern]:
        """
        Get all patterns for a user above confidence threshold.

        Args:
            user_id: User ID
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            List of BehavioralPattern objects
        """
        return [
            p for p in self.patterns.values()
            if p.user_id == user_id and p.confidence >= min_confidence
        ]

    def get_most_frequent_patterns(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[BehavioralPattern]:
        """
        Get most frequently occurring patterns for a user.

        Args:
            user_id: User ID
            limit: Max patterns to return

        Returns:
            Sorted list of patterns by frequency
        """
        user_patterns = [p for p in self.patterns.values() if p.user_id == user_id]
        return sorted(user_patterns, key=lambda p: p.frequency, reverse=True)[:limit]

    def get_most_successful_patterns(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[BehavioralPattern]:
        """
        Get patterns with highest success rates.

        Args:
            user_id: User ID
            limit: Max patterns to return

        Returns:
            Sorted list of patterns by success rate
        """
        user_patterns = [
            p for p in self.patterns.values()
            if p.user_id == user_id and p.frequency >= 2  # At least 2 observations
        ]
        return sorted(user_patterns, key=lambda p: p.success_rate, reverse=True)[:limit]

    def get_pattern_stats(self, user_id: str) -> dict[str, Any]:
        """
        Get statistics about patterns for a user.

        Returns:
            Dictionary with pattern insights
        """
        user_patterns = [p for p in self.patterns.values() if p.user_id == user_id]

        if not user_patterns:
            return {
                "total_patterns": 0,
                "high_confidence_patterns": 0,
                "average_success_rate": 0.0,
                "most_frequent": None,
                "most_successful": None,
            }

        high_conf = [p for p in user_patterns if p.is_high_confidence()]
        success_rates = [p.success_rate for p in user_patterns]
        avg_success = sum(success_rates) / len(success_rates) if success_rates else 0.0

        return {
            "total_patterns": len(user_patterns),
            "high_confidence_patterns": len(high_conf),
            "average_success_rate": avg_success,
            "most_frequent": self.get_most_frequent_patterns(user_id, 1)[0].pattern
            if user_patterns
            else None,
            "most_successful": self.get_most_successful_patterns(user_id, 1)[0].pattern
            if user_patterns
            else None,
        }

    def clear_patterns_for_user(self, user_id: str) -> None:
        """
        Clear all patterns for a user (for reset/testing).

        Args:
            user_id: User ID
        """
        to_delete = [pid for pid, p in self.patterns.items() if p.user_id == user_id]
        for pid in to_delete:
            del self.patterns[pid]
