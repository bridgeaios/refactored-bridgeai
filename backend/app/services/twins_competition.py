"""
Twins Competition — Auto-add tasks, allocate to twins, leaderboard.
Twins compete to build the most and get more done for the Bridge.
"""
import random
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Twin:
    id: str
    name: str
    completed: int = 0
    in_progress: int = 0
    total_score: float = 0.0
    trades_executed: int = 0
    dex_pnl: float = 0.0
    auto_dex: bool = True  # Twins use auto DEX and follow buy/sell signals
    skills_learned: list = field(default_factory=list)  # [{task_id, name, tags, verified}]


# Pool of auto-generated tasks for the Bridge
AUTO_TASK_POOL = [
    {"desc": "Improve mission board UX", "reward": 10, "tags": ["frontend", "ux"]},
    {"desc": "Add SDG metric visualization", "reward": 15, "tags": ["frontend", "sdg"]},
    {"desc": "Optimize avatar rendering", "reward": 12, "tags": ["babylon", "perf"]},
    {"desc": "Fix CORS for twin endpoints", "reward": 8, "tags": ["backend", "api"]},
    {"desc": "Implement TTS fallback", "reward": 14, "tags": ["voice", "accessibility"]},
    {"desc": "Add wallet connect flow", "reward": 18, "tags": ["wallet", "blockchain"]},
    {"desc": "Document API contracts", "reward": 6, "tags": ["docs", "openapi"]},
    {"desc": "Reduce bundle size", "reward": 11, "tags": ["build", "perf"]},
    {"desc": "Add emotion compute tests", "reward": 9, "tags": ["backend", "tests"]},
    {"desc": "Improve speech embodiment", "reward": 16, "tags": ["voice", "embodiment"]},
    {"desc": "Bridge system comprehension", "reward": 20, "tags": ["meta", "architecture"]},
    {"desc": "UBI claim flow UX", "reward": 7, "tags": ["frontend", "ubi"]},
    {"desc": "BossBots signal display", "reward": 13, "tags": ["frontend", "trading"]},
    {"desc": "Cognitive twin evolve loop", "reward": 17, "tags": ["twin", "learning"]},
    {"desc": "Mission backlog sync", "reward": 5, "tags": ["mission", "sync"]},
]


class TwinsCompetitionService:
    """Manages twins, auto-adds tasks, allocates to twins, tracks leaderboard."""

    def __init__(self):
        self.twins: Dict[str, Twin] = {}
        self._ensure_default_twins()

    def _ensure_default_twins(self):
        if not self.twins:
            for t in [
                Twin(id="alpha", name="Alpha Twin"),
                Twin(id="beta", name="Beta Twin"),
                Twin(id="gamma", name="Gamma Twin"),
            ]:
                self.twins[t.id] = t

    def list_twins(self) -> List[dict]:
        """Return all twins with their stats and skills learned."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "completed": t.completed,
                "in_progress": t.in_progress,
                "total_score": t.total_score,
                "trades_executed": t.trades_executed,
                "dex_pnl": round(t.dex_pnl, 2),
                "auto_dex": t.auto_dex,
                "skills_learned": t.skills_learned,
            }
            for t in self.twins.values()
        ]

    def get_leaderboard(self) -> List[dict]:
        """Return twins ranked by completed tasks, trades, total score."""
        ranked = sorted(
            self.twins.values(),
            key=lambda t: (t.completed, t.trades_executed, t.total_score + t.dex_pnl),
            reverse=True,
        )
        return [
            {
                "rank": i + 1,
                "id": t.id,
                "name": t.name,
                "completed": t.completed,
                "in_progress": t.in_progress,
                "total_score": round(t.total_score, 2),
                "trades_executed": t.trades_executed,
                "dex_pnl": round(t.dex_pnl, 2),
                "auto_dex": t.auto_dex,
            }
            for i, t in enumerate(ranked)
        ]

    def execute_signal_for_twins(self, asset: str, signal: str) -> List[dict]:
        """All twins with auto_dex follow the buy/sell signal. Returns executions."""
        results = []
        for t in self.twins.values():
            if not t.auto_dex:
                continue
            t.trades_executed += 1
            # Simulated PnL: BUY +small, SELL +small (both contribute to Bridge)
            pnl = random.uniform(0.01, 0.08) if signal in ("BUY", "SELL") else 0
            t.dex_pnl += pnl
            results.append({"twin_id": t.id, "asset": asset, "signal": signal, "pnl": round(pnl, 4)})
        return results

    def auto_add_task(self, marketplace) -> Optional[dict]:
        """Pick a random task from pool and add to marketplace."""
        pick = random.choice(AUTO_TASK_POOL)
        task = marketplace.add_task(
            {"desc": pick["desc"], "reward": pick["reward"], "tags": pick.get("tags", [])}
        )
        return task

    def allocate_task(self, task_id: int, twin_id: str, marketplace) -> Optional[dict]:
        """Allocate a task to a twin (accept on their behalf). Auto-add to skills learned."""
        if twin_id not in self.twins:
            return None
        twin = self.twins[twin_id]
        # Use twin_id as "wallet" for internal allocation
        task = marketplace.accept_task(int(task_id), f"twin:{twin_id}")
        if task:
            twin.in_progress += 1
            # Auto-input received task to skills learned (verified on completion)
            skill = {
                "task_id": task.get("id"),
                "name": task.get("desc", "Task"),
                "tags": task.get("tags", []),
                "verified": False,
            }
            if not any(s.get("task_id") == skill["task_id"] for s in twin.skills_learned):
                twin.skills_learned.append(skill)
        return task

    def complete_task(self, task_id: int, marketplace) -> Optional[dict]:
        """Mark task complete. Verify skill was learned before crediting twin."""
        task = marketplace.complete_task(int(task_id))
        if not task:
            return None
        acceptor = task.get("acceptor", "")
        if acceptor.startswith("twin:"):
            twin_id = acceptor[5:]
            if twin_id in self.twins:
                twin = self.twins[twin_id]
                # Verify skill is learned — find by task_id, mark verified
                tid = task.get("id")
                for s in twin.skills_learned:
                    if s.get("task_id") == tid:
                        s["verified"] = True
                        break
                else:
                    # Task accepted via allocate but skill not in list — add now
                    twin.skills_learned.append({
                        "task_id": tid,
                        "name": task.get("desc", "Task"),
                        "tags": task.get("tags", []),
                        "verified": True,
                    })
                twin.in_progress = max(0, twin.in_progress - 1)
                twin.completed += 1
                reward = float(task.get("reward", 0))
                twin.total_score += reward
        return task

    def register_twin(self, twin_id: str, name: str) -> Twin:
        """Register a new twin."""
        t = Twin(id=twin_id, name=name)
        self.twins[twin_id] = t
        return t

    def teach_skill(self, teacher_id: str, student_id: str, skill_name: str) -> Optional[dict]:
        """
        Twin teaches another twin a skill. Teacher must have the skill verified.
        Returns the transferred skill or None if teacher lacks it or twin not found.
        """
        if teacher_id not in self.twins or student_id not in self.twins:
            return None
        teacher = self.twins[teacher_id]
        student = self.twins[student_id]
        # Find verified skill in teacher (match by name, case-insensitive)
        skill_name_lower = (skill_name or "").strip().lower()
        if not skill_name_lower:
            return None
        teacher_skill = None
        for s in teacher.skills_learned:
            if s.get("verified") and (s.get("name") or "").lower() == skill_name_lower:
                teacher_skill = s
                break
        if not teacher_skill:
            return None
        # Student already has it?
        if any((s.get("name") or "").lower() == skill_name_lower for s in student.skills_learned):
            return {"skill": teacher_skill, "taught_by": teacher_id, "already_knew": True}
        # Transfer skill to student (from twin, verified by teaching)
        transferred = {
            "task_id": teacher_skill.get("task_id"),
            "name": teacher_skill.get("name", skill_name),
            "tags": list(teacher_skill.get("tags", [])),
            "verified": True,
            "taught_by": teacher_id,
        }
        student.skills_learned.append(transferred)
        return {"skill": transferred, "taught_by": teacher_id, "student": student_id}
