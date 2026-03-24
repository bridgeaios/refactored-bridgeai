"""
Self-Ingestion Service — TAURUS Security & Gamification Initiative.
Ingestion endpoints for GOASSL protocol, tasks, and skills into Digital Twin.
"""
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from fastapi import HTTPException

from app.services.cognitive_twin import CognitiveTwinService, SkillStack
from app.services.memory_store import MemoryStore
from app.services.mission import MissionService

logger = logging.getLogger(__name__)


SCAN_PATHS = [
    r"C:\Users\supas\.kilocode\skills",
    r"D:\skills",
    r"E:\BridgeAI\svg-engine\skills",
]


class SkillCategory(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    META = "meta"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


@dataclass
class GoASSLMessage:
    goassl_message: str
    signature: str | None = None
    timestamp: float | None = None


@dataclass
class TaskData:
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.BACKLOG


@dataclass
class SkillData:
    name: str
    category: SkillCategory
    proficiency: float = 1.0


class IngestionService:
    def __init__(self, memory: MemoryStore | None = None):
        self._memory = memory
        self._mission: MissionService | None = None
        self._twin: CognitiveTwinService | None = None
        self._stats = {
            "goassl_ingested": 0,
            "tasks_ingested": 0,
            "skills_ingested": 0,
            "last_ingestion": None,
        }

    @property
    def memory(self) -> MemoryStore:
        if self._memory is None:
            self._memory = MemoryStore()
        return self._memory

    @property
    def mission(self) -> MissionService:
        if self._mission is None:
            self._mission = MissionService(self.memory)
        return self._mission

    @property
    def twin(self) -> CognitiveTwinService:
        if self._twin is None:
            self._twin = CognitiveTwinService()
        return self._twin

    async def ingest_goassl(self, data: GoASSLMessage) -> dict[str, Any]:
        if not data.goassl_message:
            raise HTTPException(status_code=400, detail="goassl_message required")

        timestamp = data.timestamp or time.time()
        entry = {
            "goassl_message": data.goassl_message,
            "signature": data.signature,
            "timestamp": timestamp,
            "ingested_at": time.time(),
        }

        await self.memory.append("goassl_messages", entry)
        self._stats["goassl_ingested"] += 1
        self._stats["last_ingestion"] = time.time()

        logger.info(f"GOASSL message ingested: {data.goassl_message[:50]}...")

        return {
            "status": "ingested",
            "type": "goassl",
            "timestamp": timestamp,
            "total_ingested": self._stats["goassl_ingested"],
        }

    async def ingest_task(self, data: TaskData) -> dict[str, Any]:
        if not data.title:
            raise HTTPException(status_code=400, detail="title required")

        task_entry = {
            "title": data.title,
            "description": data.description,
            "priority": data.priority.value,
            "status": data.status.value,
            "source": "external_ingestion",
            "created_at": time.time(),
        }

        await self.memory.append("ingested_tasks", task_entry)

        board = await self.mission.get_counts()
        status_field = data.status.value
        if status_field in board:
            board[status_field] = board.get(status_field, 0) + 1
        board["backlog"] = board.get("backlog", 0) + 1
        await self.memory.append("mission_board", board)

        self._stats["tasks_ingested"] += 1
        self._stats["last_ingestion"] = time.time()

        logger.info(f"Task ingested: {data.title}")

        return {
            "status": "ingested",
            "type": "task",
            "task": task_entry,
            "board": board,
            "total_ingested": self._stats["tasks_ingested"],
        }

    async def ingest_skill(self, data: SkillData) -> dict[str, Any]:
        if not data.name:
            raise HTTPException(status_code=400, detail="skill name required")

        profile = self.twin.get_profile()
        skill_stack = profile.get("skill_stack", {})

        category_key = data.category.value
        current_skills = skill_stack.get(category_key, [])

        if data.name not in current_skills:
            current_skills.append(data.name)

        updated_stack = SkillStack(
            hard=skill_stack.get("hard", []),
            soft=skill_stack.get("soft", []),
            meta=skill_stack.get("meta", []),
        )

        if data.category == SkillCategory.HARD:
            updated_stack.hard = current_skills
        elif data.category == SkillCategory.SOFT:
            updated_stack.soft = current_skills
        else:
            updated_stack.meta = current_skills

        effective_skill = updated_stack.effective_skill()

        skill_entry = {
            "name": data.name,
            "category": data.category.value,
            "proficiency": data.proficiency,
            "effective_skill": effective_skill,
            "ingested_at": time.time(),
        }

        await self.memory.append("ingested_skills", skill_entry)
        await self.mission.save_skill(skill_entry)

        self._stats["skills_ingested"] += 1
        self._stats["last_ingestion"] = time.time()

        logger.info(f"Skill ingested: {data.name} ({data.category.value})")

        return {
            "status": "ingested",
            "type": "skill",
            "skill": skill_entry,
            "effective_skill": effective_skill,
            "total_ingested": self._stats["skills_ingested"],
        }

    async def get_status(self) -> dict[str, Any]:
        recent_goassl = await self.memory.get_recent("goassl_messages", 5)
        recent_tasks = await self.memory.get_recent("ingested_tasks", 5)
        recent_skills = await self.memory.get_recent("ingested_skills", 5)

        return {
            "status": "operational",
            "pipeline": "active",
            "stats": self._stats,
            "recent": {
                "goassl": len(recent_goassl),
                "tasks": len(recent_tasks),
                "skills": len(recent_skills),
            },
            "auth_required": True,
        }

    async def scan_and_import_all_skills(self) -> dict[str, Any]:
        """Scan all drives for skills and import to Digital Twin."""
        all_skills = []

        for scan_path in SCAN_PATHS:
            if not os.path.exists(scan_path):
                logger.warning(f"Scan path not found: {scan_path}")
                continue

            try:
                for root, _dirs, files in os.walk(scan_path):
                    for f in files:
                        if f.endswith(".md"):
                            skill_name = os.path.splitext(f)[0]
                            skill_path = os.path.join(root, f)
                            relative_path = os.path.relpath(skill_path, scan_path)
                            category = self._determine_category(relative_path)
                            all_skills.append({
                                "name": skill_name,
                                "category": category,
                                "source": scan_path,
                                "path": relative_path,
                            })
            except Exception as e:
                logger.error(f"Error scanning {scan_path}: {e}")

        profile = self.twin.get_profile()
        skill_stack = profile.get("skill_stack", {})

        imported_count = 0
        for skill in all_skills:
            category_key = skill["category"]
            current_skills = skill_stack.get(category_key, [])
            if skill["name"] not in current_skills:
                current_skills.append(skill["name"])
                skill_stack[category_key] = current_skills
                imported_count += 1

        await self.memory.set("skill_stack", skill_stack)
        await self.memory.set("all_scanned_skills", all_skills)

        self._stats["skills_ingested"] += imported_count
        self._stats["last_ingestion"] = time.time()

        return {
            "status": "imported",
            "total_scanned": len(all_skills),
            "newly_imported": imported_count,
            "skills_by_category": {
                cat: len([s for s in all_skills if s["category"] == cat])
                for cat in ["hard", "soft", "meta"]
            },
        }

    def _determine_category(self, path: str) -> str:
        """Determine skill category from path."""
        path_lower = path.lower()
        if any(x in path_lower for x in ["development", "coding", "programming", "backend", "frontend"]):
            return "hard"
        elif any(x in path_lower for x in ["business", "marketing", "sales", "management"]):
            return "soft"
        else:
            return "meta"


_ingestion_service: IngestionService | None = None


def get_ingestion_service() -> IngestionService:
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
