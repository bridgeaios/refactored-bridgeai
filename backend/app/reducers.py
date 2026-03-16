"""
Reducer Registry — Laws with version history.

Reducers are laws. Laws need version history.
Classification enables fine-grained permission, auditing, risk isolation.
"""
from __future__ import annotations

import hashlib
import json
import os

REGISTRY_VERSION = "1.0.0"
SPINE = "Endpoint → Reducer → State → Scheduler → Expression"

# Classification: Biology has layers
COGNITIVE = "cognitive"
STRUCTURAL = "structural"
VISUAL = "visual"
ECONOMIC = "economic"
GOVERNANCE = "governance"

REDUCER_REGISTRY = [
    {"name": "emotionOverride", "class": COGNITIVE, "version": "1.0.0"},
    {"name": "twinStateUpdate", "class": COGNITIVE, "version": "1.0.0"},
    {"name": "dialogueAppend", "class": COGNITIVE, "version": "1.0.0"},
    {"name": "missionBoardUpdate", "class": STRUCTURAL, "version": "1.0.0"},
    {"name": "skillIngest", "class": STRUCTURAL, "version": "1.0.0"},
    {"name": "faceStateUpdate", "class": VISUAL, "version": "1.0.0"},
    {"name": "marketplaceTaskUpdate", "class": ECONOMIC, "version": "1.0.0"},
    {"name": "governanceVote", "class": GOVERNANCE, "version": "1.0.0"},
]

SANCTIONED_NAMES = frozenset(r["name"] for r in REDUCER_REGISTRY)

# Strict mode ON by default. Security is not opt-in.
# Permissive requires explicit SANCTIONED_REDUCERS_STRICT=0 at boot.
STRICT_MODE = os.environ.get("SANCTIONED_REDUCERS_STRICT", "1") != "0"


def _registry_checksum() -> str:
    canonical = json.dumps(REDUCER_REGISTRY, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _identity_hash() -> str:
    parts = [REGISTRY_VERSION, SPINE, _registry_checksum(), str(STRICT_MODE)]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def is_sanctioned(name: str) -> bool:
    return name in SANCTIONED_NAMES


def reducer_class(name: str) -> str | None:
    for r in REDUCER_REGISTRY:
        if r["name"] == name:
            return r["class"]
    return None


def get_registry_snapshot() -> dict:
    """Immutable snapshot. Ties allowed mutation to system identity."""
    return {
        "version": REGISTRY_VERSION,
        "reducers": REDUCER_REGISTRY,
        "reducer_names": sorted(SANCTIONED_NAMES),
        "checksum": _registry_checksum(),
        "strict_mode": STRICT_MODE,
        "spine": SPINE,
        "identity_hash": _identity_hash(),
    }
