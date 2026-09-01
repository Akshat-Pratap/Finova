"""Finova — Integration Model."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class IntegrationProviderType(str, Enum):
    RAZORPAY = "RAZORPAY"
    STRIPE = "STRIPE"
    BANK_FEED = "BANK_FEED"


class IntegrationStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    SYNCING = "SYNCING"


class Integration(BaseModel):
    """External payment or banking provider connection."""

    integration_id: str = Field(default_factory=lambda: f"int_{uuid.uuid4().hex[:12]}")
    organization_id: str
    provider: IntegrationProviderType = IntegrationProviderType.RAZORPAY
    status: IntegrationStatus = IntegrationStatus.CONNECTED
    config: Dict[str, Any] = Field(default_factory=dict)
    masked_key_id: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    last_sync_records: int = 0
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
