"""Finova — Dataset Model."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetStatus(str, Enum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Dataset(BaseModel):
    """Uploaded financial dataset tracking entity."""

    dataset_id: str = Field(default_factory=lambda: f"ds_{uuid.uuid4().hex[:12]}")
    organization_id: str
    filename: str
    source_type: str = "csv"  # csv, json, bank_statement, razorpay, synthetic
    record_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    column_mapping: Dict[str, str] = Field(default_factory=dict)
    uploaded_by: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processing_status: DatasetStatus = DatasetStatus.UPLOADED
    processing_run_id: Optional[str] = None
    validation_errors: List[str] = Field(default_factory=list)
    raw_sample: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
