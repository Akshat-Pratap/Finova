"""Finova — Processing Run Model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    STARTED = "STARTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class ProcessingRun(BaseModel):
    """A single end-to-end reconciliation batch."""

    run_id: str = Field(default_factory=lambda: "RUN-" + __import__("uuid").uuid4().hex[:8].upper())
    status: RunStatus = RunStatus.STARTED

    # Input
    dataset_name: Optional[str] = None
    dataset_source: str = "synthetic"  # csv / json / synthetic / api

    # Counts
    records_received: int = 0
    records_valid: int = 0
    records_invalid: int = 0
    duplicates_input: int = 0

    # Results
    records_matched: int = 0
    records_ai_reviewed: int = 0
    records_manual_review: int = 0
    records_mismatch: int = 0
    records_duplicate: int = 0
    records_missing: int = 0
    exceptions_created: int = 0

    # Metrics
    match_rate: float = 0.0
    average_confidence: float = 0.0
    processing_time_seconds: float = 0.0

    # Classification metrics (only when ground truth available)
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None

    # Error
    error_message: Optional[str] = None

    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
