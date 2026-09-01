"""Finova — Cash Forecast Feature Engineering.

Prepares features from historical transaction data for forecasting.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from app.models.transaction import Transaction
from app.models.settlement import Settlement


def extract_daily_flows(
    transactions: List[Transaction],
    days: int = 30,
) -> Dict[str, Dict[str, Decimal]]:
    """
    Extract daily inflow/outflow from transactions.

    Returns dict of date_str → {inflow, outflow}.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    daily: Dict[str, Dict[str, Decimal]] = {}

    for txn in transactions:
        if txn.timestamp and txn.timestamp >= cutoff:
            date_str = txn.timestamp.date().isoformat()
            if date_str not in daily:
                daily[date_str] = {"inflow": Decimal("0"), "outflow": Decimal("0")}
            daily[date_str]["inflow"] += txn.amount

    return daily


def compute_average_daily_inflow(
    daily: Dict[str, Dict[str, Decimal]],
) -> Decimal:
    """Compute average daily inflow."""
    if not daily:
        return Decimal("0")
    total = sum(v["inflow"] for v in daily.values())
    return total / len(daily)


def compute_average_daily_outflow(
    settlements: List[Settlement],
    days: int = 30,
) -> Decimal:
    """Estimate daily outflow from settlement fees."""
    if not settlements:
        return Decimal("0")
    cutoff = datetime.utcnow() - timedelta(days=days)
    total_fees = sum(
        s.fees + s.tax
        for s in settlements
        if s.settlement_date and s.settlement_date >= cutoff
    )
    return total_fees / max(days, 1)


def pending_settlement_total(settlements: List[Settlement]) -> Decimal:
    """Sum of pending/delayed settlements."""
    from app.models.settlement import SettlementStatus
    return sum(
        s.net_amount
        for s in settlements
        if s.status in (SettlementStatus.PENDING, SettlementStatus.DELAYED)
    )
