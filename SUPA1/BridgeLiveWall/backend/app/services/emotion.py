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
        if LEARNING_AVAILABLE and self.use_model and self.model is not None:
            try:
                with torch.no_grad():
                    feats = torch.tensor([[
                        inputs.get('governance_score', 0.0),
                        inputs.get('mission_progress', 0.0),
                        inputs.get('conversation_sentiment', 0.0),
                        inputs.get('system_health', 0.0),
                        inputs.get('task_pressure', 0.0)
                    ]], dtype=torch.float32)
                    logits = self.model(feats)
                    probs = F.softmax(logits, dim=1)
                    idx = int(torch.argmax(probs, dim=1).item())
                    state = self.EMOTIONS[idx]
                    record = {"state": state, "score": float(probs.max().item()), "ts": timestamp, "inputs": inputs}
                    try:
                        await self.memory.append("emotion_history", record)
                    except Exception:
                        pass
                    return record
            except Exception as e:
                # fallback to rule-based on error
                print("Emotion model inference failed:", e)

        # rule-based fallback (and data collection)
        s = 0.0
        s += self.WEIGHTS["governance"] * (inputs.get("governance_score", 0))
        s += self.WEIGHTS["mission_progress"] * (2 * inputs.get("mission_progress", 0) - 1)
        s += self.WEIGHTS["conversation_sentiment"] * (inputs.get("conversation_sentiment", 0))
        s += self.WEIGHTS["system_health"] * (2 * inputs.get("system_health", 0) - 1)
        s += self.WEIGHTS["task_pressure"] * (1 - 2 * inputs.get("task_pressure", 0))

        if s > 0.80:
            emotion = "confident"
        elif s > 0.60:
            emotion = "focused"
        elif s > 0.40:
            emotion = "alert"
        elif s > 0.20:
            emotion = "neutral"
        elif s > 0.00:
            emotion = "reflective"
        else:
            emotion = "concerned"

        # Append to learning dataset for later training
        try:
            if LEARNING_AVAILABLE and dataset is not None:
                label = self.EMOTIONS.index(emotion) if emotion in self.EMOTIONS else 0
                dataset.append(((
                    inputs.get('governance_score', 0.0),
                    inputs.get('mission_progress', 0.0),
                    inputs.get('conversation_sentiment', 0.0),
                    inputs.get('system_health', 0.0),
                    inputs.get('task_pressure', 0.0)
                ), label))
                # attempt async-ish training trigger (non-blocking)
                try:
                    if self.learning:
                        self.learning.train_if_ready(self)
                except Exception:
                    pass
        except Exception:
            pass

        record = {"state": emotion, "score": s, "ts": timestamp, "inputs": inputs}
        try:
            await self.memory.append("emotion_history", record)
        except Exception:
            pass
        return record

