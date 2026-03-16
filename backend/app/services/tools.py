from typing import Any


class ToolsService:
    def web_search(self, query: str) -> str:
        return f"[simulated search] results for: {query}"

    def run_tool(self, name: str, payload: Any) -> dict[str, Any]:
        return {"tool": name, "status": "ok", "payload": payload}
