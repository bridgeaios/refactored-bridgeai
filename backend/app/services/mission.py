from app.services.memory_store import MemoryStore


class MissionService:
    def __init__(self, memory: MemoryStore | None = None):
        self.memory = memory or MemoryStore()

    async def get_counts(self):
        recent = await self.memory.get_recent("mission_board", 50)
        if not recent:
            # default empty board
            return {"backlog":0,"in_progress":0,"review":0,"done":0}
        latest = recent[-1]
        return {
            "backlog": latest.get("backlog",0),
            "in_progress": latest.get("in_progress",0),
            "review": latest.get("review",0),
            "done": latest.get("done",0)
        }

    async def save_skill(self, skill: dict):
        await self.memory.append("skills", skill)
        # increment backlog
        board = await self.get_counts()
        board["backlog"] = board.get("backlog",0) + 1
        await self.memory.append("mission_board", board)
        return True

    async def update_board(self, counts: dict):
        await self.memory.append("mission_board", counts)
        return True
