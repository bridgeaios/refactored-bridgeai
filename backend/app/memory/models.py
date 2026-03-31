"""
Memory Models — Data structures for Digital Twin learning

Layers:
  1. Short-term Memory — Current session execution cache
  2. Long-term Memory — Historical execution traces
  3. Patterns — Derived behavioral insights
  4. Predictions — Forecast next actions
  5. Optimization — Learned tool ordering and strategies
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MemoryTier(str, Enum):
    """Memory hierarchy."""
    SHORT_TERM = "short_term"    # Session level, volatile
    LONG_TERM = "long_term"       # Historical, persistent
    PATTERN = "pattern"           # Derived insights
    PREDICTION = "prediction"     # Forecasts
    OPTIMIZATION = "optimization"  # Learned strategies


@dataclass
class ExecutionTrace:
    """Single execution snapshot for learning."""
    execution_id: str
    user_id: str
    goal: str
    steps: list[dict]  # Tool sequence: [{"tool_id": "...", "status": "..."}]
    outcome: str  # "success" | "partial" | "failed"
    duration_ms: float
    timestamp: float
    authority: str
    context: dict[str, Any] = field(default_factory=dict)

    def tool_sequence(self) -> str:
        """Extract tool sequence as string (for pattern matching)."""
        return " → ".join([step.get("tool_id", "unknown") for step in self.steps])

    def was_successful(self) -> bool:
        """Check if execution succeeded."""
        return self.outcome == "success"


@dataclass
class BehavioralPattern:
    """Learned pattern from execution history."""
    pattern_id: str
    user_id: str
    pattern: str  # e.g., "analyzer → reporter → notifier"
    frequency: int  # How many times observed
    confidence: float  # frequency / total_executions
    last_seen: float  # Timestamp of last occurrence
    success_rate: float  # Successful outcomes / total
    avg_duration_ms: float
    tool_sequence: list[str]
    success_count: int = 0
    failure_count: int = 0

    def is_high_confidence(self) -> bool:
        """Pattern is reliable if confidence > 0.7 AND seen >= 5 times."""
        return self.confidence > 0.7 and self.frequency >= 5


@dataclass
class Prediction:
    """Forecast of likely next action."""
    prediction_id: str
    user_id: str
    context_pattern: str  # What led to this prediction
    next_action: str  # Likely next tool/step
    next_goal: Optional[str]  # Likely next goal
    confidence: float  # 0.0-1.0
    based_on_pattern: str  # Which pattern this came from
    timestamp: float


@dataclass
class OptimizationStrategy:
    """Learned optimization for a user."""
    user_id: str
    goal_pattern: str  # Goal keywords that trigger this strategy
    preferred_tool_order: list[str]  # Optimal tool sequence
    preload_tools: list[str]  # Tools to preload/cache
    skip_validation: bool = False  # Skip validation if very high confidence
    expected_duration_ms: float = 0.0
    success_rate_history: list[float] = field(default_factory=list)

    def get_average_success_rate(self) -> float:
        """Get average success rate."""
        if not self.success_rate_history:
            return 0.0
        return sum(self.success_rate_history) / len(self.success_rate_history)


@dataclass
class DigitalTwinMemory:
    """Complete memory state for a single digital twin."""
    user_id: str
    short_term: list[ExecutionTrace] = field(default_factory=list)  # Last N executions
    long_term: list[ExecutionTrace] = field(default_factory=list)  # Historical summaries
    patterns: dict[str, BehavioralPattern] = field(default_factory=dict)  # Learned patterns
    predictions: list[Prediction] = field(default_factory=list)  # Active predictions
    optimization: dict[str, OptimizationStrategy] = field(default_factory=dict)  # Strategies
    metadata: dict[str, Any] = field(default_factory=dict)  # User metadata

    # Tracking
    total_executions: int = 0
    successful_executions: int = 0
    last_updated: float = 0.0

    def learning_readiness(self) -> float:
        """
        Score (0-1) indicating how much this twin has learned.
        0: No patterns yet
        1: Stable patterns, high-confidence predictions
        """
        if not self.patterns:
            return 0.0

        high_conf = sum(1 for p in self.patterns.values() if p.is_high_confidence())
        total = len(self.patterns)
        pattern_score = high_conf / total if total > 0 else 0.0

        # Execution count score
        exec_score = min(self.total_executions / 50, 1.0)  # Stable after 50 execs

        # Average success rate
        success_score = (
            self.successful_executions / self.total_executions
            if self.total_executions > 0
            else 0.0
        )

        # Weighted average
        return (pattern_score * 0.4) + (exec_score * 0.3) + (success_score * 0.3)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "user_id": self.user_id,
            "short_term_count": len(self.short_term),
            "long_term_count": len(self.long_term),
            "pattern_count": len(self.patterns),
            "prediction_count": len(self.predictions),
            "optimization_count": len(self.optimization),
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "learning_readiness": self.learning_readiness(),
            "last_updated": self.last_updated,
        }


@dataclass
class LearningFeedback:
    """Feedback signal for reinforcement learning."""
    execution_id: str
    user_id: str
    success: bool
    reward: float  # Higher = better outcome
    penalty: float  # Higher = worse outcome
    reason: str  # Why this feedback
    timestamp: float

    def get_net_feedback(self) -> float:
        """Net signal: positive or negative."""
        return self.reward - self.penalty
