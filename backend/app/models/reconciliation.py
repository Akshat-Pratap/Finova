"""Finova — Reconciliation Result Model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    AI_REVIEW = "AI_REVIEW"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    MISMATCH = "MISMATCH"
    DUPLICATE = "DUPLICATE"
    MISSING = "MISSING"


class ConfidenceSignals(BaseModel):
    """Breakdown of confidence scoring signals."""
    reference_match: bool = False
    amount_match: bool = False
    customer_match: bool = False
    date_match: bool = False
    invoice_match: bool = False
    description_similarity: float = 0.0
    amount_difference: Optional[Decimal] = None
    date_difference_days: Optional[int] = None
    is_duplicate: bool = False
    is_fee_explainable: bool = False

    model_config = {"arbitrary_types_allowed": True}


class ReconciliationResult(BaseModel):
    """Complete reconciliation result for one transaction."""

    result_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    processing_run_id: str
    organization_id: Optional[str] = "org_default"
    dataset_id: Optional[str] = None
    transaction_id: str
    invoice_id: Optional[str] = None
    bank_transaction_id: Optional[str] = None
    settlement_id: Optional[str] = None
    customer_id: Optional[str] = None

    # Decision
    status: ReconciliationStatus
    confidence: float
    reason: str
    decision_source: str = "AUTOMATED_RULE"  # AUTOMATED_RULE | AI_ASSISTED | HUMAN_REVIEW
    signals: ConfidenceSignals = Field(default_factory=ConfidenceSignals)

    # Amounts
    expected_amount: Optional[Decimal] = None
    actual_amount: Optional[Decimal] = None
    difference: Optional[Decimal] = None

    # AI
    ai_investigated: bool = False
    ai_confidence: Optional[float] = None
    ai_finding: Optional[str] = None
    ai_recommendation: Optional[str] = None

    # Ground truth (for benchmarking)
    ground_truth_status: Optional[str] = None
    is_correct: Optional[bool] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
