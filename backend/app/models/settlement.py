"""Finova — Settlement Model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SettlementStatus(str, Enum):
    PROCESSED = "processed"
    PENDING = "pending"
    FAILED = "failed"
    DELAYED = "delayed"


class Settlement(BaseModel):
    """Canonical settlement / payout record."""

    settlement_id: str
    transaction_id: str
    gross_amount: Decimal
    fees: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    net_amount: Decimal
    settlement_date: datetime
    status: SettlementStatus = SettlementStatus.PROCESSED
    processing_run_id: Optional[str] = None
    organization_id: Optional[str] = "org_default"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
