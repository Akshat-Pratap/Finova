"""Finova — Audit Log Model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ORG_CREATED = "ORG_CREATED"
    USER_REGISTERED = "USER_REGISTERED"
    DATASET_UPLOADED = "DATASET_UPLOADED"
    DATASET_VALIDATED = "DATASET_VALIDATED"
    PROCESSING_STARTED = "PROCESSING_STARTED"
    PROCESSING_COMPLETED = "PROCESSING_COMPLETED"
    TRANSACTION_MATCHED = "TRANSACTION_MATCHED"
    TRANSACTION_MISMATCH = "TRANSACTION_MISMATCH"
    DUPLICATE_DETECTED = "DUPLICATE_DETECTED"
    AI_INVESTIGATION_STARTED = "AI_INVESTIGATION_STARTED"
    AI_INVESTIGATION_COMPLETED = "AI_INVESTIGATION_COMPLETED"
    AI_INVESTIGATION_FAILED = "AI_INVESTIGATION_FAILED"
    EXCEPTION_CREATED = "EXCEPTION_CREATED"
    EXCEPTION_ASSIGNED = "EXCEPTION_ASSIGNED"
    EXCEPTION_RESOLVED = "EXCEPTION_RESOLVED"
    EXCEPTION_REJECTED = "EXCEPTION_REJECTED"
    EXCEPTION_IGNORED = "EXCEPTION_IGNORED"
    ADJUSTMENT_RECORDED = "ADJUSTMENT_RECORDED"
    MANUAL_DECISION = "MANUAL_DECISION"
    FORECAST_GENERATED = "FORECAST_GENERATED"
    DATASET_GENERATED = "DATASET_GENERATED"
    SETTINGS_CHANGED = "SETTINGS_CHANGED"
    MEMBER_INVITED = "MEMBER_INVITED"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    INTEGRATION_CONNECTED = "INTEGRATION_CONNECTED"
    INTEGRATION_DISCONNECTED = "INTEGRATION_DISCONNECTED"
    INTEGRATION_SYNCED = "INTEGRATION_SYNCED"
    REPORT_EXPORTED = "REPORT_EXPORTED"


class AuditLog(BaseModel):
    """Immutable hash-chained audit record."""

    log_id: str = Field(default_factory=lambda: "LOG-" + __import__("uuid").uuid4().hex[:8].upper())
    organization_id: Optional[str] = "org_default"
    event_type: AuditEventType
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    processing_run_id: Optional[str] = None
    actor: str = "system"
    actor_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    event_hash: Optional[str] = None
    previous_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

