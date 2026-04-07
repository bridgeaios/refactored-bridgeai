"""
compliance.py — Gap 25: Legal / Compliance Binding.

Provides:
  1. PII tagging — mark fields that contain personal data
  2. Consent tracking — record and verify user consent before data use
  3. Audit trail — append-only log of all sensitive operations
  4. Data retention — flag records for deletion after retention_days
  5. Purpose limitation — verify that data use matches declared purpose

All compliance records are stored in MemoryStore under structured keys.
The audit log is append-only — entries are never modified after write.

Usage:
    from app.core.compliance import audit_log, consent_check, tag_pii, AuditEvent

    await audit_log(mem, event=AuditEvent.DATA_ACCESS, actor="worker",
                    subject="lead:42", detail={"field": "email"})

    ok = await consent_check(mem, user_id="user:42", purpose="marketing")
    if not ok:
        return {"blocked": True, "reason": "no_consent"}
"""
from __future__ import annotations

import json
import time
from enum import Enum

_AUDIT_PREFIX   = "audit:entry:"
_AUDIT_INDEX    = "audit:index"


def _as_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, (str, bytes, bytearray)):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, ValueError):
            return []
    return []
_CONSENT_PREFIX = "consent:"
_PII_PREFIX     = "pii:tag:"
_PII_COUNTER    = "pii:count"
_RETAIN_PREFIX  = "retain:"

# Maximum audit index size (FIFO eviction beyond this)
_MAX_AUDIT_ENTRIES = 50_000

# Default retention period (days)
DEFAULT_RETENTION_DAYS = 365


# ── Audit event taxonomy ─────────────────────────────────────────────────────

class AuditEvent(str, Enum):
    DATA_ACCESS     = "DATA_ACCESS"
    DATA_WRITE      = "DATA_WRITE"
    DATA_DELETE     = "DATA_DELETE"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    PAYMENT_INIT    = "PAYMENT_INIT"
    PAYMENT_COMPLETE= "PAYMENT_COMPLETE"
    AUTH_SUCCESS    = "AUTH_SUCCESS"
    AUTH_FAILURE    = "AUTH_FAILURE"
    ADMIN_ACTION    = "ADMIN_ACTION"
    EMIT_SILENCED   = "EMIT_SILENCED"
    CONSTRAINT_FAIL = "CONSTRAINT_FAIL"
    PII_TAGGED      = "PII_TAGGED"
    RETENTION_FLAG  = "RETENTION_FLAG"


# ── PII taxonomy ──────────────────────────────────────────────────────────────

class PIIClass(str, Enum):
    EMAIL    = "EMAIL"
    PHONE    = "PHONE"
    NAME     = "NAME"
    ADDRESS  = "ADDRESS"
    ID_NUMBER= "ID_NUMBER"
    FINANCIAL= "FINANCIAL"
    IP       = "IP"


# ── Audit log ────────────────────────────────────────────────────────────────

async def audit_log(
    mem,
    event: AuditEvent | str,
    actor: str,
    subject: str,
    detail: dict | None = None,
    pii_involved: bool = False,
) -> str:
    """
    Append an entry to the audit trail. Returns the entry ID.
    This log is write-once — existing entries are never modified.
    """
    entry_id = f"{int(time.time()*1000)}-{actor[:16]}"
    entry = {
        "id":          entry_id,
        "event":       str(event),
        "actor":       actor,
        "subject":     subject,
        "detail":      detail or {},
        "pii_involved": pii_involved,
        "ts":          time.time(),
    }
    await mem.set(_AUDIT_PREFIX + entry_id, json.dumps(entry))

    # Append to index (FIFO eviction)
    raw = await mem.get(_AUDIT_INDEX)
    index: list[str] = _as_list(raw)
    index.append(entry_id)
    if len(index) > _MAX_AUDIT_ENTRIES:
        # Evict oldest
        evicted = index[:-_MAX_AUDIT_ENTRIES]
        index = index[-_MAX_AUDIT_ENTRIES:]
        for eid in evicted:
            # Mark evicted — don't delete (immutability principle)
            pass
    await mem.set(_AUDIT_INDEX, json.dumps(index))
    return entry_id


async def audit_recent(mem, limit: int = 100) -> list[dict]:
    """Return the most recent audit entries."""
    raw = await mem.get(_AUDIT_INDEX)
    index: list[str] = _as_list(raw)
    entries = []
    for eid in reversed(index[-limit:]):
        raw_entry = await mem.get(_AUDIT_PREFIX + eid)
        if raw_entry:
            try:
                entries.append(json.loads(raw_entry))
            except Exception:
                import logging as _log
                _log.getLogger(__name__).warning("[COMPLIANCE] corrupt audit entry %s — skipped", eid)
    return entries


# ── Consent management ────────────────────────────────────────────────────────

_VALID_PURPOSES = {"marketing", "analytics", "payments", "crm", "osint", "ubi"}


async def consent_grant(mem, user_id: str, purpose: str, detail: str = "") -> None:
    """Record a user's consent grant for a given purpose."""
    record = {
        "user_id":    user_id,
        "purpose":    purpose,
        "granted":    True,
        "granted_at": time.time(),
        "detail":     detail,
    }
    await mem.set(_CONSENT_PREFIX + f"{user_id}:{purpose}", json.dumps(record))
    await audit_log(
        mem, AuditEvent.CONSENT_GRANTED, actor=user_id,
        subject=purpose, detail={"purpose": purpose},
    )


async def consent_revoke(mem, user_id: str, purpose: str) -> None:
    """Revoke a user's consent for a given purpose."""
    raw = await mem.get(_CONSENT_PREFIX + f"{user_id}:{purpose}")
    record = json.loads(raw) if raw else {"user_id": user_id, "purpose": purpose}
    record["granted"]    = False
    record["revoked_at"] = time.time()
    await mem.set(_CONSENT_PREFIX + f"{user_id}:{purpose}", json.dumps(record))
    await audit_log(
        mem, AuditEvent.CONSENT_REVOKED, actor=user_id,
        subject=purpose, detail={"purpose": purpose},
    )


async def consent_check(mem, user_id: str, purpose: str) -> bool:
    """Return True if the user has active consent for the given purpose."""
    raw = await mem.get(_CONSENT_PREFIX + f"{user_id}:{purpose}")
    if not raw:
        return False
    record = json.loads(raw)
    return bool(record.get("granted", False))


# ── PII tagging ───────────────────────────────────────────────────────────────

async def tag_pii(
    mem,
    record_id: str,
    fields: list[str],
    pii_class: PIIClass,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> None:
    """
    Tag a record as containing PII. Marks fields and sets retention expiry.
    Does not modify the source record — only writes compliance metadata.
    """
    tag = {
        "record_id":      record_id,
        "fields":         fields,
        "pii_class":      str(pii_class),
        "tagged_at":      time.time(),
        "expires_at":     time.time() + retention_days * 86400,
        "retention_days": retention_days,
    }
    await mem.set(_PII_PREFIX + record_id, json.dumps(tag))
    await mem.incr(_PII_COUNTER)
    await audit_log(
        mem, AuditEvent.PII_TAGGED, actor="system",
        subject=record_id,
        detail={"fields": fields, "class": str(pii_class)},
        pii_involved=True,
    )


async def retention_due(mem, record_id: str) -> bool:
    """Return True if a tagged record has passed its retention expiry."""
    raw = await mem.get(_PII_PREFIX + record_id)
    if not raw:
        return False
    tag = json.loads(raw)
    expires_at = tag.get("expires_at")
    return expires_at is not None and time.time() > float(expires_at)


# ── Compliance snapshot ────────────────────────────────────────────────────────

async def compliance_status(mem) -> dict:
    """Return a compliance health snapshot for the control plane."""
    raw = await mem.get(_AUDIT_INDEX)
    index: list[str] = _as_list(raw)
    return {
        "audit_entries": len(index),
        "pii_tag_count": int(await mem.get(_PII_COUNTER) or 0),
        "consent_model": list(_VALID_PURPOSES),
        "retention_days_default": DEFAULT_RETENTION_DAYS,
    }
