"""
Task Marketplace Service – post/accept/complete tasks with payments
Aligns with UN SDG 8: Decent Work and Economic Growth
This is an in-memory simulated marketplace. Production should persist
to a database and integrate escrow/payment flows via BlockchainService.
"""
from typing import Optional


class MarketplaceService:
    def __init__(self):
        self.tasks: list[dict] = []
        self._next_id = 1
        self._seen_pledge_event_ids: set[str] = set()

    def get_tasks(self, status: Optional[str] = None) -> list[dict]:
        """Get tasks. status='open' (default) | 'all' | 'in_progress' | 'completed'."""
        if status == 'all':
            return list(self.tasks)
        if status == 'in_progress':
            return [t for t in self.tasks if t.get('status') == 'in_progress']
        if status == 'completed':
            return [t for t in self.tasks if t.get('status') == 'completed']
        return [t for t in self.tasks if t.get('status') == 'open']

    def add_task(self, task: dict) -> dict:
        task_copy = task.copy()
        task_copy['id'] = self._next_id
        self._next_id += 1
        task_copy.setdefault('status', 'open')
        # Upliftment tasks may receive pledges; keep a canonical counter.
        try:
            task_copy['pledged_total'] = float(task_copy.get('pledged_total', 0) or 0)
        except Exception:
            task_copy['pledged_total'] = 0.0
        self.tasks.append(task_copy)
        return task_copy

    def accept_task(self, task_id: int, wallet: str) -> Optional[dict]:
        for t in self.tasks:
            if t.get('id') == task_id and t.get('status') == 'open':
                t['acceptor'] = wallet
                t['status'] = 'in_progress'
                # Real implementation: initialize escrow on blockchain
                return t
        return None

    def complete_task(self, task_id: int) -> Optional[dict]:
        for t in self.tasks:
            if t.get('id') == task_id and t.get('status') == 'in_progress':
                t['status'] = 'completed'
                # Real implementation: release funds from escrow
                return t
        return None

    def pledge_task(self, task_id: int, wallet: str, amount: float, event_id: str | None = None) -> Optional[dict]:
        """
        Record a pledge for an upliftment task.
        - Idempotent when event_id is provided (prevents double counting on retries).
        """
        if amount is None or amount <= 0:
            return None
        if event_id:
            if event_id in self._seen_pledge_event_ids:
                # idempotent replay: return current task state
                for t in self.tasks:
                    if t.get('id') == task_id:
                        return t
                return None
        for t in self.tasks:
            if t.get('id') == task_id:
                try:
                    t['pledged_total'] = float(t.get('pledged_total', 0) or 0) + float(amount)
                except Exception:
                    t['pledged_total'] = float(amount)
                # keep a lightweight pledge log (debugging / transparency)
                pledges = t.get('pledges')
                if not isinstance(pledges, list):
                    pledges = []
                pledges.append({"wallet": wallet, "amount": float(amount), "event_id": event_id})
                if len(pledges) > 200:
                    pledges = pledges[-200:]
                t['pledges'] = pledges
                if event_id:
                    self._seen_pledge_event_ids.add(event_id)
                return t
        return None
