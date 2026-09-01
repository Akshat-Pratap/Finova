"""Finova — Transaction Model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PaymentStatus(str, Enum):
    CAPTURED = "captured"
    AUTHORIZED = "authorized"
    FAILED = "failed"
    REFUNDED = "refunded"
    PENDING = "pending"


class PaymentMethod(str, Enum):
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    EMI = "emi"
    UNKNOWN = "unknown"


class Transaction(BaseModel):
    """Canonical transaction model."""

    transaction_id: str
    order_id: Optional[str] = None
    customer_id: str
    amount: Decimal
    currency: str = "INR"
    payment_status: PaymentStatus = PaymentStatus.CAPTURED
    payment_method: PaymentMethod = PaymentMethod.UNKNOWN
    timestamp: datetime
    reference_id: Optional[str] = None
    invoice_id: Optional[str] = None
    description: Optional[str] = None
    processing_run_id: Optional[str] = None

    # Ground truth (for benchmarking)
    ground_truth_status: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "synthetic"

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v

    model_config = {"arbitrary_types_allowed": True}
