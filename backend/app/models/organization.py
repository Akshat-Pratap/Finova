"""Finova — Organization Model."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class OrgSettings(BaseModel):
    """Configurable organization-level reconciliation tolerances & rules."""
    auto_reconcile_threshold: float = 0.90
    ai_review_threshold: float = 0.70
    amount_tolerance: float = 0.05
    fee_tolerance_percent: float = 0.05
    tax_tolerance_percent: float = 0.20
    date_tolerance_days: int = 3
    partial_payment_tolerance_percent: float = 0.10
    base_currency: str = "INR"
    confidence_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "reference": 0.30,
            "amount": 0.30,
            "customer": 0.15,
            "date": 0.10,
            "invoice": 0.10,
            "description": 0.05,
        }
    )


class Organization(BaseModel):
    """Organization / Tenant entity."""

    organization_id: str = Field(default_factory=lambda: f"org_{uuid.uuid4().hex[:12]}")
    name: str
    slug: str
    base_currency: str = "INR"
    owner_user_id: Optional[str] = None
    settings: OrgSettings = Field(default_factory=OrgSettings)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
