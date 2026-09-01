"""Finova — Fee Detector.

Detects and explains fee-related discrepancies in settlement amounts.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from app.models.settlement import Settlement
from app.models.transaction import Transaction


def detect_fee_discrepancy(
    txn: Transaction,
    settlement: Optional[Settlement],
) -> Tuple[bool, Optional[str], Decimal]:
    """
    Detect if the difference between transaction amount and settlement
    net amount is explainable as a processing fee.

    Returns (is_fee_discrepancy, explanation, difference).
    """
    if not settlement:
        return False, None, Decimal("0")

    gross = settlement.gross_amount
    net = settlement.net_amount
    fees = settlement.fees
    tax = settlement.tax
    total_deducted = fees + tax

    if gross != txn.amount:
        return False, f"Gross amount ({gross}) doesn't match transaction ({txn.amount})", abs(txn.amount - gross)

    if total_deducted > 0:
        explanation = (
            f"Settlement deducted ₹{fees:.2f} fee + ₹{tax:.2f} tax "
            f"= ₹{total_deducted:.2f} total, net ₹{net:.2f}"
        )
        return True, explanation, total_deducted

    return False, "No fees detected in settlement", Decimal("0")


def estimate_fee_from_difference(
    transaction_amount: Decimal,
    bank_amount: Decimal,
    known_fee_rates: Optional[list] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Check if the difference between transaction and bank amounts
    matches a known fee rate pattern.
    """
    if known_fee_rates is None:
        known_fee_rates = [
            Decimal("0.018"), Decimal("0.02"), Decimal("0.025"), Decimal("0.03"),
        ]

    difference = transaction_amount - bank_amount
    if difference <= 0:
        return False, None

    for rate in known_fee_rates:
        expected_fee = (transaction_amount * rate).quantize(Decimal("0.01"))
        # Allow ±₹10 variance
        if abs(difference - expected_fee) <= Decimal("10"):
            gst_on_fee = (expected_fee * Decimal("0.18")).quantize(Decimal("0.01"))
            return True, (
                f"Difference of ₹{difference:.2f} matches {float(rate)*100:.1f}% fee "
                f"(≈₹{expected_fee:.2f}) + potential GST of ₹{gst_on_fee:.2f}"
            )

    return False, None
