"""Finova — Data Validator.

Validates normalized records and generates a processing report.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.bank_transaction import BankTransaction

logger = logging.getLogger(__name__)


class ValidationReport:
    """Summary of data validation results."""

    def __init__(self):
        self.records_received: int = 0
        self.records_valid: int = 0
        self.records_invalid: int = 0
        self.duplicates_detected: int = 0
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records_received": self.records_received,
            "records_valid": self.records_valid,
            "records_invalid": self.records_invalid,
            "duplicates_detected": self.duplicates_detected,
            "validation_errors": self.validation_errors[:20],  # Truncate for response
            "warnings": self.warnings[:10],
        }


def validate_transactions(
    transactions: List[Transaction],
    duplicates_removed: int = 0,
) -> Tuple[List[Transaction], ValidationReport]:
    """
    Validate a list of normalized transactions.

    Returns (valid_transactions, report).
    """
    report = ValidationReport()
    report.records_received = len(transactions)
    report.duplicates_detected = duplicates_removed
    valid: List[Transaction] = []

    for txn in transactions:
        errors = _validate_transaction(txn)
        if errors:
            report.records_invalid += 1
            for e in errors:
                report.validation_errors.append(f"[{txn.transaction_id}] {e}")
        else:
            report.records_valid += 1
            valid.append(txn)

    logger.info(
        "Validation: %d received, %d valid, %d invalid",
        report.records_received, report.records_valid, report.records_invalid,
    )
    return valid, report


def _validate_transaction(txn: Transaction) -> List[str]:
    """Return list of validation errors for a transaction."""
    errors: List[str] = []

    if not txn.transaction_id:
        errors.append("Missing transaction_id")

    if txn.amount is None or txn.amount < 0:
        errors.append(f"Invalid amount: {txn.amount}")

    if txn.amount == Decimal("0"):
        errors.append("Zero-amount transaction")

    if not txn.customer_id:
        errors.append("Missing customer_id")

    if txn.timestamp is None:
        errors.append("Missing timestamp")

    return errors


def validate_invoices(invoices: List[Invoice]) -> Tuple[List[Invoice], List[str]]:
    """Validate invoice records."""
    valid: List[Invoice] = []
    errors: List[str] = []

    for inv in invoices:
        inv_errors = []
        if not inv.invoice_id:
            inv_errors.append("Missing invoice_id")
        if inv.invoice_amount < 0:
            inv_errors.append("Negative invoice_amount")
        if inv_errors:
            errors.extend(f"[{inv.invoice_id}] {e}" for e in inv_errors)
        else:
            valid.append(inv)

    return valid, errors
