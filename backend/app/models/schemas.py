from pydantic import BaseModel
from typing import Any

class EmotionRecord(BaseModel):
    state: str
    score: float
    ts: float
    inputs: dict[str, Any]

class MissionCounts(BaseModel):
    backlog: int
    in_progress: int
    review: int
    done: int
