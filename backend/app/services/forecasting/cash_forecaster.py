"""Finova — Cash Forecaster.

Orchestrates cash position forecasting from historical data.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from app.models.forecast import CashForecast, DailyForecast, RiskLevel
from app.models.settlement import Settlement
from app.models.transaction import Transaction
from app.services.forecasting.features import (
    extract_daily_flows,
    compute_average_daily_inflow,
    compute_average_daily_outflow,
    pending_settlement_total,
)
from app.services.forecasting.forecast_models import (
    compute_risk_level,
    generate_daily_projections,
)

logger = logging.getLogger(__name__)


def generate_forecast(
    transactions: List[Transaction],
    settlements: List[Settlement],
    processing_run_id: Optional[str] = None,
) -> CashForecast:
    """
    Generate a cash position forecast.

    Uses historical inflows and outflows to project 14 days forward.
    """
    # Feature extraction
    daily_flows = extract_daily_flows(transactions, days=30)
    avg_daily_inflow = compute_average_daily_inflow(daily_flows)
    avg_daily_outflow = compute_average_daily_outflow(settlements, days=30)
    pending = pending_settlement_total(settlements)

    # Current cash estimate — sum of last 7 days net
    total_recent = sum(
        v["inflow"] for v in list(daily_flows.values())[-7:]
    )
    # Subtract estimated fees
    current_cash = max(total_recent - (avg_daily_outflow * 7), Decimal("1000"))

    # Projections
    daily_projections = generate_daily_projections(
        current_cash=current_cash,
        avg_daily_inflow=avg_daily_inflow,
        avg_daily_outflow=avg_daily_outflow,
        days=14,
    )

    def _net_at_day(n: int) -> Decimal:
        if n <= len(daily_projections):
            return Decimal(str(daily_projections[n - 1]["net_position"]))
        return current_cash

    # Risk assessment
    risk_level, risk_factors = compute_risk_level(
        current_cash=current_cash,
        projected_7d=_net_at_day(7) - current_cash,
        pending_outflows=avg_daily_outflow * 7,
    )

    # Build DailyForecast objects
    daily_forecast_objs = [
        DailyForecast(
            forecast_date=p["forecast_date"],
            projected_inflow=Decimal(str(p["projected_inflow"])),
            projected_outflow=Decimal(str(p["projected_outflow"])),
            net_position=Decimal(str(p["net_position"])),
            confidence=p["confidence"],
        )
        for p in daily_projections
    ]

    forecast = CashForecast(
        forecast_id=f"FCT-{uuid.uuid4().hex[:8].upper()}",
        processing_run_id=processing_run_id,
        current_cash=current_cash,
        forecast_1_day=_net_at_day(1),
        forecast_3_days=_net_at_day(3),
        forecast_7_days=_net_at_day(7),
        forecast_14_days=_net_at_day(14),
        risk_level=risk_level,
        risk_factors=risk_factors,
        daily_breakdown=daily_forecast_objs,
        pending_settlements=pending,
        outstanding_invoices=Decimal("0"),
    )

    logger.info(
        "Forecast generated: current=₹%.2f, 7d=₹%.2f, risk=%s",
        float(current_cash), float(forecast.forecast_7_days), risk_level.value,
    )
    return forecast


def generate_demo_forecast() -> CashForecast:
    """Generate a realistic demo forecast without real data."""
    from app.services.data_generator import generate_dataset

    txns, _, _, settlements = generate_dataset(num_records=100, seed=99)
    return generate_forecast(txns, settlements)
