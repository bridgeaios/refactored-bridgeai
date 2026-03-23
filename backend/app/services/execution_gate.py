"""
Execution Gate - Binary execution gate for task validation.

Enforces:
- Theta constraint: task type must be in {'F','P','J','X'}
- Value constraint: revenue + impact + trust - cost > 0
- Singleton execution: only highest-value task selected per cycle
"""
from dataclasses import dataclass
from typing import Optional

THETA = {"F", "P", "J", "X"}


@dataclass
class ScoredTask:
    task: dict
    score: float
    reason: str


def evaluate(task: dict) -> Optional[ScoredTask]:
    """Validate task type and compute value score."""
    if task.get("type") not in THETA:
        return None

    value = (
        task.get("revenue", 0)
        + task.get("impact", 0)
        + task.get("trust", 0)
        - task.get("cost", 0)
    )

    if value <= 0:
        return None

    return ScoredTask(task=task, score=value, reason="passed_gate")


def select(tasks: list[dict]) -> Optional[ScoredTask]:
    """Select highest value task (singleton execution)."""
    valid = [t for t in (evaluate(x) for x in tasks) if t]
    if not valid:
        return None
    return max(valid, key=lambda x: x.score)