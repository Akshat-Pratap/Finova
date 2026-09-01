"""Finova — Audit Log Model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    DATASET_UPLOADED = "DATASET_UPLOADED"
    PROCESSING_STARTED = "PROCESSING_STARTED"
    PROCESSING_COMPLETED = "PROCESSING_COMPLETED"
    TRANSACTION_MATCHED = "TRANSACTION_MATCHED"
    TRANSACTION_MISMATCH = "TRANSACTION_MISMATCH"
    DUPLICATE_DETECTED = "DUPLICATE_DETECTED"
    AI_INVESTIGATION_STARTED = "AI_INVESTIGATION_STARTED"
    AI_INVESTIGATION_COMPLETED = "AI_INVESTIGATION_COMPLETED"
    AI_INVESTIGATION_FAILED = "AI_INVESTIGATION_FAILED"
    EXCEPTION_CREATED = "EXCEPTION_CREATED"
    EXCEPTION_RESOLVED = "EXCEPTION_RESOLVED"
    EXCEPTION_REJECTED = "EXCEPTION_REJECTED"
    EXCEPTION_IGNORED = "EXCEPTION_IGNORED"
    MANUAL_DECISION = "MANUAL_DECISION"
    FORECAST_GENERATED = "FORECAST_GENERATED"
    DATASET_GENERATED = "DATASET_GENERATED"


class AuditLog(BaseModel):
    """Immutable audit record."""

    log_id: str = Field(default_factory=lambda: "LOG-" + __import__("uuid").uuid4().hex[:8].upper())
    event_type: AuditEventType
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    processing_run_id: Optional[str] = None
    actor: str = "system"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
