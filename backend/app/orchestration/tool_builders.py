"""
Tool Builders — Convert existing services into EHSA tools.

Pattern:
  Existing service → adapt to tool interface → register in registry

Each tool gets:
  - Input schema (parameters)
  - Output schema (return values)
  - Executor (async wrapper around service method)
  - Authority requirement
"""
from __future__ import annotations

from typing import Any, Callable

from app.orchestration.tool_registry import Tool, ToolCategory, ToolSchema, register_tool


def build_analysis_tool(
    tool_id: str,
    name: str,
    description: str,
    service_executor: Callable,
    authority_required: str = "public",
) -> Tool:
    """
    Build an analysis tool from a service method.

    Example:
        async def analyze_leads(data: dict) -> dict:
            # ... analysis logic
            return {"insights": [...]}

        tool = build_analysis_tool(
            tool_id="crm.analyze_leads",
            name="Analyze Leads",
            description="Analyze CRM leads for patterns",
            service_executor=analyze_leads,
        )
    """
    return Tool(
        id=tool_id,
        name=name,
        category=ToolCategory.ANALYSIS,
        description=description,
        input_schema=ToolSchema(
            required_fields=["data"],
            optional_fields=["filters", "metrics"],
            return_type="dict",
        ),
        output_schema=ToolSchema(
            required_fields=["insights"],
            optional_fields=["metadata"],
            return_type="dict",
        ),
        authority_required=authority_required,
        executor=service_executor,
    )


def build_transformation_tool(
    tool_id: str,
    name: str,
    description: str,
    service_executor: Callable,
    authority_required: str = "economic",
) -> Tool:
    """Build a transformation tool from a service method."""
    return Tool(
        id=tool_id,
        name=name,
        category=ToolCategory.TRANSFORMATION,
        description=description,
        input_schema=ToolSchema(
            required_fields=["input"],
            optional_fields=["options", "metadata"],
            return_type="dict",
        ),
        output_schema=ToolSchema(
            required_fields=["output"],
            optional_fields=["stats"],
            return_type="dict",
        ),
        authority_required=authority_required,
        executor=service_executor,
    )


def build_communication_tool(
    tool_id: str,
    name: str,
    description: str,
    service_executor: Callable,
    authority_required: str = "public",
) -> Tool:
    """Build a communication tool from a service method."""
    return Tool(
        id=tool_id,
        name=name,
        category=ToolCategory.COMMUNICATION,
        description=description,
        input_schema=ToolSchema(
            required_fields=["message"],
            optional_fields=["recipient", "channel"],
            return_type="dict",
        ),
        output_schema=ToolSchema(
            required_fields=["status"],
            optional_fields=["message_id"],
            return_type="dict",
        ),
        authority_required=authority_required,
        executor=service_executor,
    )


def build_execution_tool(
    tool_id: str,
    name: str,
    description: str,
    service_executor: Callable,
    authority_required: str = "internal",
) -> Tool:
    """Build an execution tool from a service method."""
    return Tool(
        id=tool_id,
        name=name,
        category=ToolCategory.EXECUTION,
        description=description,
        input_schema=ToolSchema(
            required_fields=["action"],
            optional_fields=["params", "context"],
            return_type="dict",
        ),
        output_schema=ToolSchema(
            required_fields=["status"],
            optional_fields=["result", "metadata"],
            return_type="dict",
        ),
        authority_required=authority_required,
        executor=service_executor,
    )


def build_retrieval_tool(
    tool_id: str,
    name: str,
    description: str,
    service_executor: Callable,
    authority_required: str = "public",
) -> Tool:
    """Build a retrieval/read tool from a service method."""
    return Tool(
        id=tool_id,
        name=name,
        category=ToolCategory.RETRIEVAL,
        description=description,
        input_schema=ToolSchema(
            required_fields=[],
            optional_fields=["filters", "limit", "offset"],
            return_type="list",
        ),
        output_schema=ToolSchema(
            required_fields=[],
            optional_fields=["data", "count"],
            return_type="list",
        ),
        authority_required=authority_required,
        executor=service_executor,
    )


# =============================================================================
# Registration Helpers
# =============================================================================


def register_crm_tools() -> None:
    """Register CRM domain tools."""
    # These are stubs — actual implementations will wrap real CRM service methods

    async def analyze_leads(data: dict, **kwargs) -> dict:
        """Analyze leads for patterns and score."""
        return {
            "output": {
                "total_leads": len(data.get("leads", [])),
                "insights": ["pattern_1", "pattern_2"],
            }
        }

    async def process_lead(input: dict, **kwargs) -> dict:
        """Process and score a single lead."""
        return {"output": {"lead_id": "123", "score": 0.85}}

    tool1 = build_analysis_tool(
        tool_id="crm.analyze_leads",
        name="Analyze Leads",
        description="Analyze CRM leads for patterns and insights",
        service_executor=analyze_leads,
        authority_required="public",
    )

    tool2 = build_transformation_tool(
        tool_id="crm.process_lead",
        name="Process Lead",
        description="Process and score a single lead",
        service_executor=process_lead,
        authority_required="economic",
    )

    register_tool(tool1)
    register_tool(tool2)


def register_analytics_tools() -> None:
    """Register analytics tools."""

    async def summarize_data(data: dict, **kwargs) -> dict:
        """Summarize data."""
        return {"output": {"summary": "Key insights from data"}}

    async def generate_report(data: dict, **kwargs) -> dict:
        """Generate a structured report."""
        return {"output": {"report": "Detailed analysis report"}}

    tool1 = build_analysis_tool(
        tool_id="analytics.summarize",
        name="Summarize Data",
        description="Summarize input data",
        service_executor=summarize_data,
        authority_required="public",
    )

    tool2 = build_transformation_tool(
        tool_id="analytics.report",
        name="Generate Report",
        description="Generate a structured report from data",
        service_executor=generate_report,
        authority_required="economic",
    )

    register_tool(tool1)
    register_tool(tool2)


def register_communication_tools() -> None:
    """Register communication tools."""

    async def send_email(message: dict, **kwargs) -> dict:
        """Send an email message."""
        return {"output": {"status": "sent", "message_id": "msg_123"}}

    async def send_notification(message: dict, **kwargs) -> dict:
        """Send a notification."""
        return {"output": {"status": "sent", "notification_id": "notif_123"}}

    tool1 = build_communication_tool(
        tool_id="comms.email",
        name="Send Email",
        description="Send an email message",
        service_executor=send_email,
        authority_required="public",
    )

    tool2 = build_communication_tool(
        tool_id="comms.notify",
        name="Send Notification",
        description="Send a notification",
        service_executor=send_notification,
        authority_required="public",
    )

    register_tool(tool1)
    register_tool(tool2)
