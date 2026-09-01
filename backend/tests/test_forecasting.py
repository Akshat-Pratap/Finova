"""Finova — Tests: Forecasting."""
import pytest
from decimal import Decimal

from app.services.forecasting.cash_forecaster import generate_forecast, generate_demo_forecast
from app.services.forecasting.forecast_models import compute_risk_level, generate_daily_projections
from app.models.forecast import RiskLevel


def test_demo_forecast_returns_valid():
    forecast = generate_demo_forecast()
    assert forecast.current_cash >= 0
    assert forecast.forecast_7_days >= 0
    assert forecast.risk_level in list(RiskLevel)
    assert len(forecast.daily_breakdown) == 14


def test_forecast_with_empty_data():
    """Forecast with no transactions should still return valid result."""
    forecast = generate_forecast([], [])
    assert forecast.current_cash >= 0
    assert forecast.forecast_7_days >= 0


def test_risk_level_high():
    risk, factors = compute_risk_level(
        current_cash=Decimal("100000"),
        projected_7d=Decimal("-50000"),  # Big decline
        pending_outflows=Decimal("0"),
    )
    assert risk == RiskLevel.HIGH
    assert len(factors) > 0


def test_risk_level_low():
    risk, factors = compute_risk_level(
        current_cash=Decimal("1000000"),
        projected_7d=Decimal("50000"),   # Increase
        pending_outflows=Decimal("10000"),
    )
    assert risk == RiskLevel.LOW


def test_daily_projections_14_days():
    projections = generate_daily_projections(
        current_cash=Decimal("500000"),
        avg_daily_inflow=Decimal("50000"),
        avg_daily_outflow=Decimal("5000"),
        days=14,
    )
    assert len(projections) == 14
    for p in projections:
        assert "forecast_date" in p
        assert "net_position" in p
        assert p["confidence"] > 0


def test_forecast_with_transactions():
    from app.services.data_generator import generate_dataset
    txns, _, _, settlements = generate_dataset(50, seed=42)
    forecast = generate_forecast(txns, settlements)
    assert forecast.current_cash > 0
    assert isinstance(forecast.risk_level, RiskLevel)
