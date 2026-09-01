"""Finova — Report Model."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    RECONCILIATION = "RECONCILIATION"
    EXCEPTIONS = "EXCEPTIONS"
    TRANSACTIONS = "TRANSACTIONS"
    AUDIT_LOG = "AUDIT_LOG"
    PROCESSING_RUN = "PROCESSING_RUN"


class ReportFormat(str, Enum):
    CSV = "CSV"
    JSON = "JSON"


class Report(BaseModel):
    """Generated financial report export record."""

    report_id: str = Field(default_factory=lambda: f"rep_{uuid.uuid4().hex[:12]}")
    organization_id: str
    report_type: ReportType
    format: ReportFormat = ReportFormat.CSV
    filename: str
    record_count: int = 0
    generated_by: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
