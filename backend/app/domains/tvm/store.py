"""In-memory TVM store and recommendation library (replace with KV `tvm:` prefix per manifest)."""
from __future__ import annotations

from typing import Any, Optional

from app.domains.tvm.models import TVMRow

# recommendation_code -> metadata used by proposal / approval flow
RECOMMENDATION_LIB: dict[str, dict[str, Any]] = {
    "MP-AF-ROTATE-TOKEN": {
        "requires_human_approval": False,
        "steps": [
            "Revoke existing token",
            "Issue new token from Treasury",
            "Update MailPipeline config with new token",
            "Restart MailPipeline service",
            "Re-check health probe",
        ],
    },
    "MP-HUMAN-ESCALATION": {
        "requires_human_approval": True,
        "steps": ["Notify operator", "Hold until human decision"],
    },
}

_TVM_STORE: dict[str, dict[str, Any]] = {}


def reset_store() -> None:
    """Clear store (tests)."""
    _TVM_STORE.clear()


def seed_demo_row() -> None:
    """Idempotent seed for MailPipeline demo topic."""
    if "MailPipeline" in _TVM_STORE:
        return
    _TVM_STORE["MailPipeline"] = {
        "topic": "MailPipeline",
        "configured": 1,
        "healthy": 0,
        "degraded": 1,
        "action_required": 1,
        "autofix_available": 1,
        "human_approval_needed": 1,
        "last_updated": 0,
        "recommendation_code": None,
        "signature": None,
    }


def get_all_rows() -> list[dict[str, Any]]:
    seed_demo_row()
    return list(_TVM_STORE.values())


def get_row(topic: str) -> Optional[dict[str, Any]]:
    seed_demo_row()
    return _TVM_STORE.get(topic)


def put_row(row: dict[str, Any]) -> dict[str, Any]:
    topic = row["topic"]
    _TVM_STORE[topic] = row
    return row


def row_to_model(d: dict[str, Any]) -> TVMRow:
    return TVMRow.model_validate(d)
