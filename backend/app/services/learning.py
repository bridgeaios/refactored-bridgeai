import torch
import torch.nn as nn
import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from typing import List, Tuple
import asyncio

# Simple global in-memory dataset; persisted strategies should replace this in production
dataset: List[Tuple[Tuple[float,float,float,float,float], int]] = []

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts')
os.makedirs(ARTIFACT_DIR, exist_ok=True)

class EmotionModel(nn.Module):
    def __init__(self):
        super(EmotionModel, self).__init__()
        self.fc1 = nn.Linear(5, 32)
        self.fc2 = nn.Linear(32, 16)
        self.fc3 = nn.Linear(16, 6)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class LearningService:
    def __init__(self):
        self.threshold = 100
        self.epochs = 8
        self.is_training = False
        self.last_trained_ts = None
        self.last_loss = None

    def update_with_sample(self, inputs, label:int):
        dataset.append((tuple(inputs), int(label)))

    def _do_train(self, emotion_service):
        # synchronous training executed in a thread
        if len(dataset) < self.threshold:
            return False
        device = torch.device('cpu')
        X = torch.tensor([d[0] for d in dataset], dtype=torch.float32, device=device)
        y = torch.tensor([d[1] for d in dataset], dtype=torch.long, device=device)
        ds = TensorDataset(X,y)
        loader = DataLoader(ds, batch_size=16, shuffle=True)
        model = EmotionModel().to(device)
        opt = optim.Adam(model.parameters(), lr=1e-3)
        loss_fn = nn.CrossEntropyLoss()
        model.train()
        last_loss = None
        for epoch in range(self.epochs):
            epoch_loss = 0.0
            for xb,yb in loader:
                opt.zero_grad()
                out = model(xb)
                loss = loss_fn(out, yb)
                loss.backward()
                opt.step()
                epoch_loss += loss.item()
            last_loss = epoch_loss / max(1, len(loader))
        # persist model
        path = os.path.join(ARTIFACT_DIR, 'emotion_model.pt')
        torch.save(model.state_dict(), path)
        emotion_service.model = model
        emotion_service.use_model = True
        self.last_trained_ts = time.time()
        self.last_loss = last_loss
        return True

    async def train(self, emotion_service):
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

    def get_status(self):
        return {
            'is_training': bool(self.is_training),
            'last_trained_ts': float(self.last_trained_ts) if self.last_trained_ts else None,
            'last_loss': float(self.last_loss) if self.last_loss else None,
            'samples': len(dataset)
        }


class LearningService:
    def __init__(self, threshold: int = 100):
        self.threshold = threshold
        self._trained = False

    def add_sample(self, inputs: Tuple[float, ...], label: int):
        dataset.append((inputs, label))

    def ready(self) -> bool:
        return len(dataset) >= self.threshold and not self._trained

    def train(self) -> nn.Module | None:
        if not self.ready():
            return None

        inputs = torch.tensor([d[0] for d in dataset], dtype=torch.float32)
        labels = torch.tensor([d[1] for d in dataset], dtype=torch.long)
        ds = TensorDataset(inputs, labels)
        loader = DataLoader(ds, batch_size=32, shuffle=True)

        model = EmotionModel(input_dim=inputs.shape[1])
        criterion = nn.CrossEntropyLoss()
        optimz = optim.Adam(model.parameters(), lr=1e-3)

        for epoch in range(8):
            for xb, yb in loader:
                optimz.zero_grad()
                out = model(xb)
                loss = criterion(out, yb)
                loss.backward()
                optimz.step()

        self._trained = True
        return model
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from typing import List, Tuple

# Global in-memory dataset used for bootstrapping the emotion model
dataset: List[Tuple[Tuple[float,float,float,float,float], int]] = []

class EmotionModel(nn.Module):
    def __init__(self):
        super(EmotionModel, self).__init__()
        self.fc1 = nn.Linear(5, 32)
        self.bn1 = nn.BatchNorm1d(32)
        self.fc2 = nn.Linear(32, 64)
        self.bn2 = nn.BatchNorm1d(64)
        self.fc3 = nn.Linear(64, 32)
        self.bn3 = nn.BatchNorm1d(32)
        self.fc4 = nn.Linear(32, 6)
        self.dropout = nn.Dropout(0.3)

    def forward(self, x):
        x = torch.relu(self.bn1(self.fc1(x)))
        x = self.dropout(x)
        x = torch.relu(self.bn2(self.fc2(x)))
        x = self.dropout(x)
        x = torch.relu(self.bn3(self.fc3(x)))
        x = self.fc4(x)
        return x

class LearningService:
    def __init__(self):
        self.threshold = 100
        self.epochs = 12
        self.batch_size = 16

    def update_with_sample(self, inputs, label: int):
        dataset.append((tuple(inputs), int(label)))

    # alias for compatibility
    def update_with_feedback(self, *args, **kwargs):
        return self.update_with_sample(*args, **kwargs)

    def train_if_ready(self, emotion_service):
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
        for epoch in range(self.epochs):
            for xb, yb in loader:
                opt.zero_grad()
                out = model(xb)
                loss = loss_fn(out, yb)
                loss.backward()
                opt.step()
        emotion_service.model = model
        emotion_service.use_model = True
        return True

    def get_status(self):
        return {
            "is_training": False,
            "last_trained_ts": None,
            "last_loss": None,
            "samples": len(dataset),
        }
