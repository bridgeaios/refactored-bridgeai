import asyncio
import os
import time
from typing import Any, cast

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Simple global in-memory dataset; persisted strategies should replace this in production
dataset: list[tuple[tuple[float, float, float, float, float], int]] = []

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts')
os.makedirs(ARTIFACT_DIR, exist_ok=True)


class EmotionModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.fc1 = nn.Linear(5, 32)
        self.fc2 = nn.Linear(32, 16)
        self.fc3 = nn.Linear(16, 6)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)  # type: ignore[no-any-return]


class LearningService:
    def __init__(self) -> None:
        self.threshold = 100
        self.epochs = 8
        self.batch_size = 16
        self.is_training = False
        self.last_trained_ts: float | None = None
        self.last_loss: float | None = None

    def update_with_sample(self, inputs: Any, label: int) -> None:
        t = cast(tuple[float, float, float, float, float], tuple(inputs))
        dataset.append((t, int(label)))

    def update_with_feedback(self, *args: Any, **kwargs: Any) -> None:
        self.update_with_sample(*args, **kwargs)

    def _do_train(self, emotion_service: Any) -> bool:
        if len(dataset) < self.threshold:
            return False
        device = torch.device('cpu')
        X = torch.tensor([d[0] for d in dataset], dtype=torch.float32, device=device)
        y = torch.tensor([d[1] for d in dataset], dtype=torch.long, device=device)
        ds = TensorDataset(X, y)
        loader = DataLoader(ds, batch_size=self.batch_size, shuffle=True)
        model = EmotionModel().to(device)
        opt = optim.Adam(model.parameters(), lr=1e-3)
        loss_fn = nn.CrossEntropyLoss()
        model.train()
        last_loss = None
        for _epoch in range(self.epochs):
            epoch_loss = 0.0
            for xb, yb in loader:
                opt.zero_grad()
                out = model(xb)
                loss = loss_fn(out, yb)
                loss.backward()
                opt.step()
                epoch_loss += loss.item()
            last_loss = epoch_loss / max(1, len(loader))
        path = os.path.join(ARTIFACT_DIR, 'emotion_model.pt')
        torch.save(model.state_dict(), path)
        emotion_service.model = model
        emotion_service.use_model = True
        self.last_trained_ts = time.time()
        self.last_loss = last_loss
        return True

    def train_if_ready(self, emotion_service: Any) -> bool:
        return self._do_train(emotion_service)

    async def train(self, emotion_service: Any) -> bool:
        if self.is_training:
            return False
        if len(dataset) < self.threshold:
            return False
        self.is_training = True
        try:
            result = await asyncio.to_thread(self._do_train, emotion_service)
            return result
        finally:
            self.is_training = False

    def get_status(self) -> dict[str, Any]:
        return {
            'is_training': bool(self.is_training),
            'last_trained_ts': float(self.last_trained_ts) if self.last_trained_ts else None,
            'last_loss': float(self.last_loss) if self.last_loss else None,
            'samples': len(dataset),
        }
