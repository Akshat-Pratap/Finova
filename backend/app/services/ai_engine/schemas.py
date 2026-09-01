"""Finova — AI Investigation Response Schemas."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class AIInvestigationResponse(BaseModel):
    """Validated AI investigation response."""

    finding: str = Field(..., description="Brief finding label")
    reason: str = Field(..., description="Evidence-based explanation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence 0-1")
    recommendation: str = Field(..., description="RECONCILE / MANUAL_REVIEW / REJECT")
    requires_manual_review: bool = Field(default=False)
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence points")

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        valid = {"RECONCILE", "MANUAL_REVIEW", "REJECT"}
        normalized = v.upper().strip()
        if normalized not in valid:
            return "MANUAL_REVIEW"
        return normalized

    @field_validator("finding")
    @classmethod
    def finding_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            return "Unable to determine"
        return v.strip()
