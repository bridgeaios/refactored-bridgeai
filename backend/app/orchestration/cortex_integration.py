"""
Cortex Integration Layer — Unified tracing and authority enforcement.

Integrates EHSA Orchestrator with Cortex authority system.

Responsibilities:
  - Send execution traces to Cortex
  - Enforce authority constraints during planning/execution
  - Log all decisions for audit trail
  - Handle capability flags (perception, trade, evolution, etc.)
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.cortex import (
    AUTHORITY_SCOPES,
    AuthorityClass,
    capability_enabled,
    get_capability_audit_log,
)
from app.orchestration.execution_loop import ExecutionResult
from app.orchestration.orchestrator import EHSA


class CortexIntegratedEHSA(EHSA):
    """
    EHSA with Cortex integration.

    Enforces:
    - Authority-based tool access
    - Capability gating
    - Unified audit trail
    - Trace emission to Cortex
    """

    async def execute(
        self,
        goal: str,
        twin_context: Optional[dict[str, Any]] = None,
        authority: str = "public",
        cortex_callback: Optional[callable] = None,
    ) -> ExecutionResult:
        """
        Execute with Cortex integration.

        Args:
            goal: High-level goal
            twin_context: Digital twin memory
            authority: Authority level (from JWT)
            cortex_callback: Optional callback(trace) for Cortex integration

        Returns:
            ExecutionResult
        """
        # Validate authority
        if authority not in [a.value for a in AuthorityClass]:
            return ExecutionResult(
                plan_id="error",
                goal=goal,
                status="failed",
                error=f"Invalid authority: {authority}",
            )

        # Check capability flags
        if not self._check_capabilities(authority):
            return ExecutionResult(
                plan_id="error",
                goal=goal,
                status="failed",
                error=f"Required capabilities disabled for authority: {authority}",
            )

        # Execute with parent implementation
        result = await super().execute(
            goal=goal,
            twin_context=twin_context,
            authority=authority,
        )

        # Emit to Cortex
        if cortex_callback:
            for trace in result.trace:
                await cortex_callback(
                    {
                        "type": "orchestration_step",
                        "execution_id": result.plan_id,
                        "goal": goal,
                        "authority": authority,
                        "step": trace.to_dict(),
                        "timestamp": time.time(),
                    }
                )

        return result

    def _check_capabilities(self, authority: str) -> bool:
        """
        Check if required capabilities are enabled for this authority.

        Authority levels:
        - PUBLIC: perception, speech
        - ECONOMIC: marketplace, ubi, trade
        - INTERNAL: state_mutation
        - ORCHESTRATOR: evolution, system
        """
        required_caps = {
            "public": ["perception", "speech"],
            "economic": ["marketplace", "ubi", "trade"],
            "internal": ["state_mutation"],
            "orchestrator": ["evolution"],
        }

        caps = required_caps.get(authority, [])
        for cap in caps:
            if not capability_enabled(cap):
                return False

        return True

    def get_authority_scope(self, authority: str) -> set[str]:
        """Get the scope of operations for an authority level."""
        auth_class = AuthorityClass(authority)
        return AUTHORITY_SCOPES.get(auth_class, set())

    def get_scoped_tools(self, authority: str) -> list[dict]:
        """
        Get tools available to an authority level.

        Respects:
        - Authority hierarchy
        - Capability flags
        - Scope constraints
        """
        available = super().list_tools()

        # Filter by authority
        auth_scope = self.get_authority_scope(authority)
        scoped = [
            t for t in available
            if t["authority_required"].lower() in auth_scope or authority == "orchestrator"
        ]

        # Filter by capabilities
        cap_map = {
            "analysis": "perception",
            "communication": "speech",
            "execution": "state_mutation",
        }

        filtered = []
        for tool in scoped:
            required_cap = cap_map.get(tool["category"])
            if required_cap and not capability_enabled(required_cap):
                continue
            filtered.append(tool)

        return filtered
