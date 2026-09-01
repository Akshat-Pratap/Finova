"""Finova — AI Investigation Model."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AIInvestigation(BaseModel):
    """Record of an AI investigation."""

    investigation_id: str = Field(default_factory=lambda: "INV-" + __import__("uuid").uuid4().hex[:8].upper())
    exception_id: str
    transaction_id: Optional[str] = None
    processing_run_id: str

    # AI provider info
    provider: str  # "gemini" or "DEMO MODE"
    model_version: Optional[str] = None

    # Input context (stored for auditability)
    input_context: Dict[str, Any] = Field(default_factory=dict)

    # AI output
    finding: str
    reason: str
    confidence: float
    recommendation: str  # RECONCILE / MANUAL_REVIEW / REJECT
    requires_manual_review: bool
    evidence: List[str] = Field(default_factory=list)

    # Response metadata
    raw_response: Optional[str] = None
    is_fallback: bool = False
    retry_count: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
