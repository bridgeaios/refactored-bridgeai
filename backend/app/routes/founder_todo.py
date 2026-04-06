"""
Founder TODO — personal objective tracker linked to the digital twin wallpaper.

GET  /api/founder-todo          → current todo list
PATCH /api/founder-todo/{id}/complete → mark objective complete
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.deps import get_memory

router = APIRouter(tags=["founder"])

_KEY = "founder:todo"

_DEFAULT: dict[str, Any] = {
    "version": 1,
    "updatedAt": None,
    "objectives": [
        {"id": "obj-1", "title": "Ship Phase 4 - Frontend Control Surface",  "status": "pending",  "completedAt": None},
        {"id": "obj-2", "title": "Stabilize Bridge Live Wall integration",    "status": "pending",  "completedAt": None},
        {"id": "obj-3", "title": "AWS credentials configured",                "status": "pending",  "completedAt": None},
        {"id": "obj-4", "title": "Skills pipeline composable",                "status": "pending",  "completedAt": None},
        {"id": "obj-5", "title": "Dashboard + Installer live (3000/7777)",    "status": "complete", "completedAt": None},
    ],
}


@router.get("/founder-todo")
async def get_founder_todo() -> dict[str, Any]:
    mem = get_memory()
    data = await mem.get(_KEY)
    return data if isinstance(data, dict) else _DEFAULT


@router.patch("/founder-todo/{objective_id}/complete")
async def complete_objective(objective_id: str) -> dict[str, Any]:
    mem = get_memory()
    data = await mem.get(_KEY)
    todo: dict[str, Any] = data if isinstance(data, dict) else dict(_DEFAULT)

    for obj in todo.get("objectives", []):
        if obj["id"] == objective_id:
            obj["status"] = "complete"
            obj["completedAt"] = time.time()
            todo["updatedAt"] = time.time()
            await mem.set(_KEY, todo)
            return todo

    raise HTTPException(status_code=404, detail=f"Objective {objective_id!r} not found")
