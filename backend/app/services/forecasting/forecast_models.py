"""Finova — Forecast Models.

Simple, interpretable cash position forecasting.
No unnecessary ML complexity — uses moving averages and trend analysis.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from app.models.forecast import RiskLevel


def simple_moving_average_forecast(
    daily_inflows: List[Decimal],
    window: int = 7,
) -> Decimal:
    """7-day moving average inflow forecast."""
    if not daily_inflows:
        return Decimal("0")
    recent = daily_inflows[-window:]
    return sum(recent) / len(recent)


def compute_risk_level(
    current_cash: Decimal,
    projected_7d: Decimal,
    pending_outflows: Decimal = Decimal("0"),
) -> Tuple[RiskLevel, List[str]]:
    """
    Determine risk level based on cash trajectory.

    Returns (risk_level, risk_factors).
    """
    risk_factors: List[str] = []
    effective_cash = current_cash + projected_7d - pending_outflows

    if effective_cash < Decimal("0"):
        risk_factors.append("Projected negative cash position in 7 days")
        return RiskLevel.CRITICAL, risk_factors

    ratio = float(projected_7d / current_cash) if current_cash > 0 else 0

    if ratio < -0.3:
        risk_factors.append("Cash projected to decline by >30% in 7 days")
        return RiskLevel.HIGH, risk_factors

    if ratio < -0.1:
        risk_factors.append("Cash projected to decline by 10-30% in 7 days")
        if pending_outflows > current_cash * Decimal("0.5"):
            risk_factors.append("Pending outflows exceed 50% of current cash")
        return RiskLevel.MEDIUM, risk_factors

    if pending_outflows > current_cash * Decimal("0.3"):
        risk_factors.append("Pending outflows exceed 30% of current cash")
        return RiskLevel.MEDIUM, risk_factors

    return RiskLevel.LOW, risk_factors


def generate_daily_projections(
    current_cash: Decimal,
    avg_daily_inflow: Decimal,
    avg_daily_outflow: Decimal,
    days: int = 14,
) -> List[Dict]:
    """Generate day-by-day cash projections."""
    projections = []
    running_cash = current_cash

    for i in range(1, days + 1):
        forecast_date = (date.today() + timedelta(days=i)).isoformat()
        # Add slight randomness factor (±10%) for realism
        inflow_var = avg_daily_inflow * Decimal("0.9")
        outflow_var = avg_daily_outflow * Decimal("1.05")
        net = inflow_var - outflow_var
        running_cash = max(running_cash + net, Decimal("0"))

        projections.append({
            "forecast_date": forecast_date,
            "projected_inflow": float(inflow_var),
            "projected_outflow": float(outflow_var),
            "net_position": float(running_cash),
            "confidence": max(0.60, 0.95 - i * 0.02),  # Confidence decays over time
        })

    return projections
