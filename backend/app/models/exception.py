"""Finova — Exception Model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExceptionType(str, Enum):
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_REFERENCE = "MISSING_REFERENCE"
    DUPLICATE = "DUPLICATE"
    PARTIAL_PAYMENT = "PARTIAL_PAYMENT"
    FEE_DISCREPANCY = "FEE_DISCREPANCY"
    TAX_DISCREPANCY = "TAX_DISCREPANCY"
    DATE_MISMATCH = "DATE_MISMATCH"
    MISSING_TRANSACTION = "MISSING_TRANSACTION"
    UNKNOWN_PAYMENT = "UNKNOWN_PAYMENT"
    CUSTOMER_MISMATCH = "CUSTOMER_MISMATCH"


class ExceptionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExceptionStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class FinovaException(BaseModel):
    """Financial exception requiring human attention."""

    exception_id: str = Field(default_factory=lambda: "EX-" + __import__("uuid").uuid4().hex[:8].upper())
    processing_run_id: str
    transaction_id: Optional[str] = None
    result_id: Optional[str] = None

    type: ExceptionType
    severity: ExceptionSeverity = ExceptionSeverity.MEDIUM
    description: str

    expected_value: Optional[Decimal] = None
    actual_value: Optional[Decimal] = None
    difference: Optional[Decimal] = None

    # AI investigation results
    ai_finding: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_recommendation: Optional[str] = None
    ai_evidence: Optional[list] = None
    ai_requires_manual_review: bool = True

    # Status
    status: ExceptionStatus = ExceptionStatus.OPEN
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
