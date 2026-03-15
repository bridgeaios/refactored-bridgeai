"""
SDG Tracker – monitors alignment with UN Sustainable Development Goals
Tracks simple metrics like UBI claims and marketplace activity.
This module is intentionally lightweight and meant for display/telemetry.
"""
from typing import Dict


class SdgService:
    def __init__(self):
        self.metrics: Dict[str, int] = {
            'ubi_claims': 0,
            'tasks_created': 0,
            'tasks_completed': 0,
            'trades_executed': 0,
        }

    def track(self, key: str, value: int = 1) -> None:
        if key in self.metrics:
            self.metrics[key] += value

    def get_metrics(self) -> Dict[str, int]:
        return dict(self.metrics)
