"""Finova — Bank Transaction Model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BankTransaction(BaseModel):
    """Canonical bank transaction / statement entry."""

    bank_transaction_id: str
    date: datetime
    amount: Decimal
    description: Optional[str] = None
    reference: Optional[str] = None
    account: Optional[str] = None
    processing_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
