import time
from typing import Dict
from app.services.memory_store import MemoryStore
import time
from typing import Dict
import torch
import torch.nn.functional as F
from app.services.memory_store import MemoryStore
from app.services import learning

class EmotionService:
    EMOTIONS = ["neutral", "focused", "confident", "alert", "reflective", "concerned"]

    def __init__(self, memory: MemoryStore | None = None):
        self.memory = memory or MemoryStore()
        self.model = None
        self.use_model = False

    async def compute(self, inputs: Dict) -> Dict:
        # normalize / extract expected fields
        votes = float(inputs.get("votes", inputs.get("governance_score", 0)))
        backlog = float(inputs.get("backlog", inputs.get("backlog_count", 0)))
        in_progress = float(inputs.get("in_progress", inputs.get("in_progress_count", 0)))
        sentiment = float(inputs.get("sentiment", inputs.get("conversation_sentiment", 0.0)))
        health = float(inputs.get("health", inputs.get("system_health", 1.0)))

        record = {"inputs": {"votes": votes, "backlog": backlog, "in_progress": in_progress, "sentiment": sentiment, "health": health}}
        timestamp = time.time()

        if self.use_model and self.model is not None:
            try:
                tensor = torch.tensor([[votes, backlog, in_progress, sentiment, health]], dtype=torch.float32)
                with torch.no_grad():
                    out = self.model(tensor)
                    probs = F.softmax(out, dim=1)
                    idx = int(torch.argmax(probs).item())
                    state = self.EMOTIONS[idx]
                    record.update({"state": state, "probs": probs.tolist(), "ts": timestamp})
                    try:
                        await self.memory.append("emotion_history", record)
                    except Exception:
                        pass
                    return record
            except Exception:
                # fallback to rule-based if model fails
                self.use_model = False

        # rule-based fallback and dataset collection for learning
        score = (votes * 0.2) - (backlog * 0.1) - (in_progress * 0.05) + (sentiment * 0.3) + (health * 0.35)
        if score > 0.8:
            emotion = "confident"
        elif score > 0.6:
            emotion = "focused"
        elif score > 0.4:
            emotion = "alert"
        elif score > 0.2:
            emotion = "neutral"
        elif score > 0:
            emotion = "reflective"
        else:
            emotion = "concerned"

        # append a labeled sample for offline training
        try:
            label = self.EMOTIONS.index(emotion)
            learning.dataset.append(((votes, backlog, in_progress, sentiment, health), label))
        except Exception:
            pass

        record.update({"state": emotion, "score": score, "ts": timestamp})
        try:
            await self.memory.append("emotion_history", record)
        except Exception:
            pass
        return record
