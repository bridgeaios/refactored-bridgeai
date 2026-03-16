"""
BossBots – AI trading bots for passive income
This is a placeholder service. In production this would host the ML/strategy
code, risk controls, and trade execution integrations.
"""
import random


class BossBotsService:
    def __init__(self):
        self._signals: list[dict] = []

    def generate_signal(self, asset: str) -> str:
        signal = "BUY" if random.random() > 0.5 else "SELL"
        self._signals.append({"asset": asset, "signal": signal})
        return signal

    def get_signals(self) -> list[dict]:
        return list(self._signals[-10:])
