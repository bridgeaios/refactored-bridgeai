from typing import Any


class ToolsService:
    def web_search(self, query: str) -> str:
        # Simulated search result; replace with actual integration when allowed
        return f"Simulated search result for: {query}"

    def run_tool(self, name: str, payload: Any) -> dict:
        # Generic tool runner placeholder
        return {"tool": name, "status": "ok", "payload": payload}
class ToolsService:
    def web_search(self, query: str) -> str:
        # Local simulated search implementation
        return f"[simulated search] results for: {query}"

    def run_tool(self, name: str, payload: dict) -> dict:
        # stubbed tool runner; add connectors as needed
        return {"ok": False, "reason": "tool_not_available"}
