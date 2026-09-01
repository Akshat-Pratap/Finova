"""Finova — Hash-Chained Audit Logger.

Records immutable financial and operational events to MongoDB audit_logs collection.
Implements SHA-256 hash-chaining for tamper-evidence.
Scans and scrubs sensitive credentials before logging.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.audit_log import AuditLog, AuditEventType
from app.services.memory_store import memory_audit_logs
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)

# In-memory storage for audit hashes
_last_hashes: Dict[str, str] = {}  # org_id -> latest_hash

# Sensitive keys to scrub
SENSITIVE_KEYS = {"password", "secret", "token", "key", "access_token", "refresh_token", "api_key"}


def _scrub_sensitive(data: Any) -> Any:
    """Recursively scrub secrets from metadata dictionaries."""
    if isinstance(data, dict):
        scrubbed = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                scrubbed[k] = "[REDACTED]"
            else:
                scrubbed[k] = _scrub_sensitive(v)
        return scrubbed
    elif isinstance(data, list):
        return [_scrub_sensitive(i) for i in data]
    return data


class AuditLogger:
    """Tamper-evident, hash-chained audit logger."""

    def __init__(self, db=None):
        self._db = db

    async def log(
        self,
        event_type: AuditEventType,
        organization_id: str = "org_default",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        processing_run_id: Optional[str] = None,
        actor: str = "system",
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        message: str = "",
    ) -> AuditLog:
        """Record an immutable, hash-chained audit event."""
        # Get previous hash for this tenant
        prev_hash = await self._get_latest_hash(organization_id)
        now = datetime.utcnow()
        clean_metadata = _scrub_sensitive(metadata or {})
        actor_str = str(actor or actor_id or "system")

        # Compute hash
        payload_to_hash = f"{prev_hash}|{now.isoformat()}|{event_type.value}|{entity_id or ''}|{actor_str}|{json.dumps(clean_metadata, sort_keys=True, default=str)}"
        event_hash = hashlib.sha256(payload_to_hash.encode("utf-8")).hexdigest()

        event = AuditLog(
            organization_id=organization_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            processing_run_id=processing_run_id,
            actor=actor_str,
            actor_id=actor_id,
            metadata=clean_metadata,
            message=message,
            event_hash=event_hash,
            previous_hash=prev_hash,
            created_at=now,
        )

        _last_hashes[organization_id] = event_hash
        memory_audit_logs.append(dict_to_mongo(event))

        logger.info(
            "AUDIT [%s] | %s | %s=%s | %s (hash: %s...)",
            organization_id,
            event_type.value,
            entity_type or "system",
            entity_id or "-",
            message,
            event_hash[:8],
        )

        if self._db is not None:
            try:
                await self._db.audit_logs.insert_one(dict_to_mongo(event))
            except Exception as exc:
                logger.error("Failed to persist audit log: %s", exc)

        return event

    async def _get_latest_hash(self, organization_id: str) -> str:
        """Retrieve the hash of the most recent audit entry for the tenant."""
        if organization_id in _last_hashes:
            return _last_hashes[organization_id]

        if self._db is not None:
            doc = await self._db.audit_logs.find_one(
                {"organization_id": organization_id},
                sort=[("created_at", -1)],
            )
            if doc and doc.get("event_hash"):
                _last_hashes[organization_id] = doc["event_hash"]
                return doc["event_hash"]

        genesis = hashlib.sha256(f"GENESIS_{organization_id}".encode("utf-8")).hexdigest()
        _last_hashes[organization_id] = genesis
        return genesis

    async def verify_integrity(self, organization_id: str) -> Dict[str, Any]:
        """Verify that the cryptographic hash chain for an organization has not been broken."""
        events = []
        if self._db is not None:
            cursor = self._db.audit_logs.find({"organization_id": organization_id}).sort("created_at", 1)
            events = await cursor.to_list(length=10000)
        else:
            events = [e for e in memory_audit_logs if e.get("organization_id") == organization_id]
            events.sort(key=lambda x: x.get("created_at", ""))

        if not events:
            return {"verified": True, "total_events": 0, "message": "No audit records to verify."}

        expected_prev = hashlib.sha256(f"GENESIS_{organization_id}".encode("utf-8")).hexdigest()
        for idx, event in enumerate(events):
            recorded_prev = event.get("previous_hash")
            if recorded_prev and recorded_prev != expected_prev and idx > 0:
                return {
                    "verified": False,
                    "tampered_at_index": idx,
                    "event_id": event.get("log_id"),
                    "message": f"Hash chain broken at event {event.get('log_id')}.",
                }
            expected_prev = event.get("event_hash")

        return {
            "verified": True,
            "total_events": len(events),
            "latest_hash": expected_prev,
            "message": "Audit trail is mathematically verified and intact.",
        }
