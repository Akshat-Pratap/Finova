"""Finova — Data Cleaner.

Handles missing values, malformed records, invalid amounts/dates, and duplicates.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Tuple

from app.utils.dates import parse_date

logger = logging.getLogger(__name__)


class CleaningResult:
    """Result of the data cleaning step."""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self.removed: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.duplicates_removed: int = 0
        self.invalid_removed: int = 0

    @property
    def records_cleaned(self) -> int:
        return len(self.records)


def clean_transactions(records: List[Dict[str, Any]]) -> CleaningResult:
    """Clean and deduplicate transaction records."""
    result = CleaningResult()
    seen_ids: set = set()

    for raw in records:
        cleaned, errors = _clean_transaction_record(raw)
        if errors:
            result.errors.extend(errors)
            result.invalid_removed += 1
            result.removed.append(raw)
            continue

        txn_id = cleaned.get("transaction_id")
        if txn_id and txn_id in seen_ids:
            logger.debug("Duplicate transaction_id removed: %s", txn_id)
            result.duplicates_removed += 1
            result.removed.append(raw)
            continue

        if txn_id:
            seen_ids.add(txn_id)

        result.records.append(cleaned)

    logger.info(
        "Cleaned transactions: %d valid, %d invalid, %d duplicates",
        result.records_cleaned, result.invalid_removed, result.duplicates_removed,
    )
    return result


def clean_invoices(records: List[Dict[str, Any]]) -> CleaningResult:
    """Clean invoice records."""
    result = CleaningResult()
    seen_ids: set = set()

    for raw in records:
        cleaned, errors = _clean_invoice_record(raw)
        if errors:
            result.errors.extend(errors)
            result.invalid_removed += 1
            continue

        inv_id = cleaned.get("invoice_id")
        if inv_id and inv_id in seen_ids:
            result.duplicates_removed += 1
            continue
        if inv_id:
            seen_ids.add(inv_id)

        result.records.append(cleaned)

    return result


def clean_bank_transactions(records: List[Dict[str, Any]]) -> CleaningResult:
    """Clean bank statement records."""
    result = CleaningResult()
    seen_ids: set = set()

    for raw in records:
        cleaned, errors = _clean_bank_record(raw)
        if errors:
            result.errors.extend(errors)
            result.invalid_removed += 1
            continue

        bank_id = cleaned.get("bank_transaction_id")
        if bank_id and bank_id in seen_ids:
            result.duplicates_removed += 1
            continue
        if bank_id:
            seen_ids.add(bank_id)

        result.records.append(cleaned)

    return result


def clean_settlements(records: List[Dict[str, Any]]) -> CleaningResult:
    """Clean settlement records."""
    result = CleaningResult()
    for raw in records:
        cleaned, errors = _clean_settlement_record(raw)
        if errors:
            result.errors.extend(errors)
            result.invalid_removed += 1
            continue
        result.records.append(cleaned)
    return result


# ---------------------------------------------------------------------------
# Internal cleaners
# ---------------------------------------------------------------------------

def _clean_amount(value: Any) -> Tuple[Optional[Decimal], Optional[str]]:
    if value is None:
        return None, "Missing amount"
    try:
        d = Decimal(str(value))
        if d < 0:
            return None, f"Negative amount: {value}"
        return d, None
    except InvalidOperation:
        return None, f"Invalid amount: {value}"


def _clean_transaction_record(raw: Dict) -> Tuple[Dict, List[str]]:
    errors: List[str] = []
    cleaned = dict(raw)

    # Required: transaction_id
    if not cleaned.get("transaction_id"):
        errors.append("Missing transaction_id")

    # Required: amount
    amount, err = _clean_amount(cleaned.get("amount"))
    if err:
        errors.append(err)
    else:
        cleaned["amount"] = str(amount)

    # Required: customer_id
    if not cleaned.get("customer_id"):
        # Try to default from name if present
        if cleaned.get("customer_name"):
            cleaned["customer_id"] = f"CUST-{abs(hash(cleaned['customer_name'])) % 10000:04d}"
        else:
            cleaned["customer_id"] = "CUST-UNKNOWN"

    # Date
    ts = cleaned.get("timestamp") or cleaned.get("date") or cleaned.get("created_at")
    if ts:
        parsed = parse_date(str(ts)) if not hasattr(ts, "isoformat") else ts
        if parsed:
            cleaned["timestamp"] = parsed.isoformat() if hasattr(parsed, "isoformat") else str(parsed)
        else:
            errors.append(f"Unparseable date: {ts}")

    # Normalize optional reference
    if cleaned.get("reference_id"):
        cleaned["reference_id"] = str(cleaned["reference_id"]).strip()

    return cleaned, errors


def _clean_invoice_record(raw: Dict) -> Tuple[Dict, List[str]]:
    errors: List[str] = []
    cleaned = dict(raw)

    if not cleaned.get("invoice_id"):
        errors.append("Missing invoice_id")

    for field in ("invoice_amount", "total_amount"):
        val, err = _clean_amount(cleaned.get(field))
        if err:
            errors.append(f"{field}: {err}")
        else:
            cleaned[field] = str(val)

    tax, err = _clean_amount(cleaned.get("tax", 0))
    if tax is not None:
        cleaned["tax"] = str(tax)

    return cleaned, errors


def _clean_bank_record(raw: Dict) -> Tuple[Dict, List[str]]:
    errors: List[str] = []
    cleaned = dict(raw)

    if not cleaned.get("bank_transaction_id"):
        errors.append("Missing bank_transaction_id")

    val, err = _clean_amount(cleaned.get("amount"))
    if err:
        errors.append(err)
    else:
        cleaned["amount"] = str(val)

    return cleaned, errors


def _clean_settlement_record(raw: Dict) -> Tuple[Dict, List[str]]:
    errors: List[str] = []
    cleaned = dict(raw)

    for field in ("gross_amount", "net_amount"):
        val, err = _clean_amount(cleaned.get(field))
        if err:
            errors.append(f"{field}: {err}")
        else:
            cleaned[field] = str(val)

    return cleaned, errors
