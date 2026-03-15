import asyncio
import os
import random


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


class AutomationLoops:
    """
    Dynamic learn→do→pay loop cycling through all twins.

    Runs on the server so the UI can be passive and still show life:
    - Auto-add marketplace tasks
    - Auto-allocate tasks across alpha/beta/gamma
    - Auto-complete tasks (verifies skills)
    - Auto DEX signals (twins follow, PnL updates)
    - Mission board sync from marketplace truth
    """

    def __init__(self, mission, marketplace, twins, bossbots, revenue, sdg, replication=None):
        self.mission = mission
        self.marketplace = marketplace
        self.twins = twins
        self.replication = replication
        self.bossbots = bossbots
        self.revenue = revenue
        self.sdg = sdg
        self._tasks: list[asyncio.Task] = []
        self._stop = asyncio.Event()

        self.enabled = os.getenv("BRIDGE_AUTOMATION", "1") not in ("0", "false", "False")
        self.auto_add_sec = _env_int("BRIDGE_AUTO_ADD_SEC", 60)
        self.auto_allocate_sec = _env_int("BRIDGE_AUTO_ALLOCATE_SEC", 12)
        self.auto_complete_sec = _env_int("BRIDGE_AUTO_COMPLETE_SEC", 20)
        self.auto_dex_sec = _env_int("BRIDGE_AUTO_DEX_SEC", 45)
        self.board_sync_sec = _env_int("BRIDGE_BOARD_SYNC_SEC", 10)
        self.replication_sec = _env_int("BRIDGE_REPLICATION_SEC", 90)
        self.replication_engine = replication

        self._alloc_idx = 0

    def start(self) -> None:
        if not self.enabled:
            return
        tasks = [
            asyncio.create_task(self._loop_auto_add(), name="bridge:auto_add"),
            asyncio.create_task(self._loop_auto_allocate(), name="bridge:auto_allocate"),
            asyncio.create_task(self._loop_auto_complete(), name="bridge:auto_complete"),
            asyncio.create_task(self._loop_auto_dex(), name="bridge:auto_dex"),
            asyncio.create_task(self._loop_sync_board(), name="bridge:sync_board"),
        ]
        if self.replication_engine:
            tasks.append(asyncio.create_task(self._loop_replication(), name="bridge:replication"))
        self._tasks = tasks

    async def stop(self) -> None:
        self._stop.set()
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

    async def _sleep(self, sec: int) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=max(1, sec))
        except asyncio.TimeoutError:
            return

    def _twin_ids(self) -> list[str]:
        ids = list(getattr(self.twins, "twins", {}).keys())
        return ids or ["alpha", "beta", "gamma"]

    async def _loop_auto_add(self):
        # Seed at boot.
        try:
            if len(self.marketplace.get_tasks(status="all")) < 3:
                for _ in range(3):
                    self.twins.auto_add_task(self.marketplace)
                    self.sdg.track("tasks_created", 1)
        except Exception:
            pass
        while not self._stop.is_set():
            await self._sleep(self.auto_add_sec)
            try:
                self.twins.auto_add_task(self.marketplace)
                self.sdg.track("tasks_created", 1)
            except Exception:
                pass

    async def _loop_auto_allocate(self):
        while not self._stop.is_set():
            await self._sleep(self.auto_allocate_sec)
            try:
                open_tasks = self.marketplace.get_tasks(status=None)
                if not open_tasks:
                    continue
                twins = self._twin_ids()
                # deterministic-ish round-robin across twins
                twin_id = twins[self._alloc_idx % len(twins)]
                self._alloc_idx += 1
                t = random.choice(open_tasks)
                self.twins.allocate_task(int(t.get("id")), twin_id, self.marketplace)
            except Exception:
                pass

    async def _loop_auto_complete(self):
        while not self._stop.is_set():
            await self._sleep(self.auto_complete_sec)
            try:
                in_prog = self.marketplace.get_tasks(status="in_progress")
                if not in_prog:
                    continue
                t = random.choice(in_prog)
                completed = self.twins.complete_task(int(t.get("id")), self.marketplace)
                if completed:
                    self.sdg.track("tasks_completed", 1)
                    # payout loop: completion generates fee/yield which funds buckets
                    try:
                        reward = float(completed.get("reward", 0))
                        self.revenue.collect(max(0.01, reward * 0.02))
                    except Exception:
                        pass
            except Exception:
                pass

    async def _loop_auto_dex(self):
        assets = ["BTC", "ETH", "BRDG", "SOL"]
        while not self._stop.is_set():
            await self._sleep(self.auto_dex_sec)
            try:
                asset = random.choice(assets)
                signal = self.bossbots.generate_signal(asset)
                execs = self.twins.execute_signal_for_twins(asset, signal)
                if execs:
                    self.sdg.track("trades_executed", 1)
                    self.revenue.collect(0.05)
            except Exception:
                pass

    async def _loop_sync_board(self):
        while not self._stop.is_set():
            await self._sleep(self.board_sync_sec)
            try:
                open_tasks = self.marketplace.get_tasks(status=None)
                in_prog = self.marketplace.get_tasks(status="in_progress")
                done = self.marketplace.get_tasks(status="completed")
                counts = {
                    "backlog": len(open_tasks),
                    "in_progress": len(in_prog),
                    "review": 0,
                    "done": len(done),
                }
                await self.mission.update_board(counts)
            except Exception:
                pass

    async def _loop_replication(self):
        """Replication engine: task demand > capacity or performance > threshold → create twin / add task."""
        while not self._stop.is_set():
            await self._sleep(self.replication_sec)
            try:
                if self.replication_engine:
                    await self.replication_engine.evaluate()
            except Exception:
                pass

