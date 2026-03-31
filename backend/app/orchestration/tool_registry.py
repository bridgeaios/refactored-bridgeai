"""
Tool Registry — Single source of truth for all available tools/services.

EHSA can only call tools defined here. Apps cannot self-invoke.
Registry enables tool selection during planning phase.

Tool = (name, description, input_schema, output_schema, executor)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class ToolCategory(str, Enum):
    """Tool categories for decision logic."""
    ANALYSIS = "analysis"           # Data analysis, insights
    TRANSFORMATION = "transformation"  # Data processing, mutation
    COMMUNICATION = "communication"   # Email, notifications, outreach
    EXECUTION = "execution"          # Business logic execution
    VALIDATION = "validation"         # Data validation, verification
    RETRIEVAL = "retrieval"           # Data fetching, reads
    PERSISTENCE = "persistence"       # State mutation, writes


@dataclass
class ToolSchema:
    """Input/output schema for tool invocation."""
    required_fields: list[str]
    optional_fields: list[str]
    return_type: str  # e.g. "dict", "list", "bool"


@dataclass
class Tool:
    """Tool definition — what EHSA can invoke."""
    id: str  # Unique identifier (e.g., "crm.ingest_lead")
    name: str
    category: ToolCategory
    description: str
    input_schema: ToolSchema
    output_schema: ToolSchema
    authority_required: str  # Min authority to invoke (PUBLIC, ECONOMIC, INTERNAL, ORCHESTRATOR)
    executor: Callable[..., Awaitable[dict[str, Any]]]  # Async function to call


class ToolRegistry:
    """
    Registry of all available tools.

    EHSA planning engine queries this to select appropriate tools for each step.
    Single source of truth — no tool invocation outside this registry.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry."""
        if tool.id in self._tools:
            raise ValueError(f"Tool {tool.id} already registered")
        self._tools[tool.id] = tool

    def get(self, tool_id: str) -> Tool | None:
        """Retrieve a tool by ID."""
        return self._tools.get(tool_id)

    def list_by_category(self, category: ToolCategory) -> list[Tool]:
        """List all tools in a category."""
        return [t for t in self._tools.values() if t.category == category]

    def list_by_authority(self, authority: str) -> list[Tool]:
        """List tools available to a given authority level."""
        # Map authority hierarchy: PUBLIC < ECONOMIC < INTERNAL < ORCHESTRATOR
        authority_levels = {
            "public": 1,
            "economic": 2,
            "internal": 3,
            "orchestrator": 4,
        }
        user_level = authority_levels.get(authority.lower(), 0)
        return [
            t for t in self._tools.values()
            if authority_levels.get(t.authority_required.lower(), 0) <= user_level
        ]

    def all_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    async def invoke(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Invoke a tool by ID with given parameters.

        Returns:
            dict with 'output' key and status information
        """
        tool = self.get(tool_id)
        if not tool:
            return {"error": f"Tool {tool_id} not found", "status": "error"}

        try:
            result = await tool.executor(**params)
            return {
                "status": "success",
                "output": result,
                "tool_id": tool_id,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "tool_id": tool_id,
            }


# Global registry instance
_REGISTRY: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ToolRegistry()
    return _REGISTRY


def register_tool(tool: Tool) -> None:
    """Register a tool in the global registry."""
    get_registry().register(tool)
