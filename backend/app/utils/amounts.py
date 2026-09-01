"""Finova — Monetary amount utilities using Decimal."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Optional


def to_decimal(value) -> Optional[Decimal]:
    """Convert any numeric value to Decimal safely."""
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None


def format_inr(amount: Decimal) -> str:
    """Format Decimal as INR string."""
    return f"₹{amount:,.2f}"


def amounts_match(a: Decimal, b: Decimal, tolerance: Decimal = Decimal("0")) -> bool:
    """Check if two amounts match within tolerance."""
    return abs(a - b) <= tolerance


def percentage_difference(expected: Decimal, actual: Decimal) -> Decimal:
    """Calculate percentage difference."""
    if expected == 0:
        return Decimal("0")
    return abs(expected - actual) / expected * Decimal("100")


def safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Safe division, returns 0 if denominator is 0."""
    if denominator == Decimal("0"):
        return Decimal("0")
    return numerator / denominator
