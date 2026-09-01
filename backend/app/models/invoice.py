"""Finova — Invoice Model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InvoiceStatus(str, Enum):
    PAID = "paid"
    UNPAID = "unpaid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(BaseModel):
    """Canonical invoice model."""

    invoice_id: str
    customer_id: str
    invoice_amount: Decimal
    tax: Decimal = Decimal("0")
    total_amount: Decimal
    date: datetime
    due_date: Optional[datetime] = None
    status: InvoiceStatus = InvoiceStatus.UNPAID
    description: Optional[str] = None
    processing_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("invoice_amount", "tax", "total_amount")
    @classmethod
    def amount_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v

    model_config = {"arbitrary_types_allowed": True}
