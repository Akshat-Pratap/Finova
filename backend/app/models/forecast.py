"""Finova — Cash Forecast Model."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DailyForecast(BaseModel):
    """Single-day cash forecast."""
    forecast_date: date
    projected_inflow: Decimal
    projected_outflow: Decimal
    net_position: Decimal
    confidence: float

    model_config = {"arbitrary_types_allowed": True}


class CashForecast(BaseModel):
    """Overall cash position forecast."""

    forecast_id: str = Field(default_factory=lambda: "FCT-" + __import__("uuid").uuid4().hex[:8].upper())
    processing_run_id: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    current_cash: Decimal
    forecast_1_day: Decimal
    forecast_3_days: Decimal
    forecast_7_days: Decimal
    forecast_14_days: Decimal

    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_factors: List[str] = Field(default_factory=list)

    daily_breakdown: List[DailyForecast] = Field(default_factory=list)

    pending_settlements: Decimal = Decimal("0")
    outstanding_invoices: Decimal = Decimal("0")

    model_config = {"arbitrary_types_allowed": True}
