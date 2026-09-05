"""Finova — Generic Dataset Type-Aware Validation.

Provides source-specific validation profiles without requiring
transaction_id for every financial source.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from app.models.dataset import DatasetType, get_validation_profile
from app.utils.dates import parse_date
from app.utils.amounts import to_decimal

logger = logging.getLogger(__name__)


class DatasetValidationReport:
    """Structured validation report for a dataset."""

    def __init__(self, dataset_type: str):
        self.dataset_type: str = dataset_type
        self.records_received: int = 0
        self.records_valid: int = 0
        self.records_invalid: int = 0
        self.duplicates_detected: int = 0
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []
        self.diagnostics: List[Dict[str, Any]] = []  # per-row structured

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_type": self.dataset_type,
            "records_received": self.records_received,
            "records_valid": self.records_valid,
            "records_invalid": self.records_invalid,
            "duplicates_detected": self.duplicates_detected,
            "validation_errors": self.validation_errors[:50],
            "warnings": self.warnings[:20],
            "diagnostics_sample": self.diagnostics[:10],
        }


def _has_amount(record: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if record has any valid amount field."""
    # Check multiple amount field variants
    amount_fields = ["amount", "invoice_amount", "total_amount", "gross_amount", "net_amount"]
    for f in amount_fields:
        val = record.get(f)
        if val is not None and str(val).strip() != "":
            dec = to_decimal(val)
            if dec is not None and dec >= 0 and dec != Decimal("0"):
                return True, f
            if dec is not None and dec == Decimal("0"):
                return False, f"Zero-amount in {f}"
            # invalid amount
            continue
    # If no amount field found at all
    has_any = any(record.get(f) is not None and str(record.get(f)).strip() != "" for f in amount_fields)
    if has_any:
        return False, "Invalid amount format"
    return False, "Missing amount (no amount/invoice_amount/total_amount/gross_amount/net_amount)"


def _has_timestamp(record: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if record has parseable timestamp/date."""
    ts = record.get("timestamp") or record.get("date") or record.get("created_at")
    if ts is None or str(ts).strip() == "":
        return False, "Missing timestamp/date"
    parsed = parse_date(str(ts)) if not hasattr(ts, "isoformat") else ts
    if parsed is None:
        return False, f"Unparseable date: {ts}"
    return True, ""


def _has_identifier(record: Dict[str, Any], any_of: List[str]) -> Tuple[bool, str]:
    """Check if record has at least one of the identifier fields."""
    for fid in any_of:
        val = record.get(fid)
        if val is not None and str(val).strip() != "":
            return True, fid
    return False, f"Missing required identifier: need one of {any_of}"


def validate_records_for_type(
    records: List[Dict[str, Any]],
    dataset_type: str,
    duplicates_removed: int = 0,
) -> Tuple[List[Dict[str, Any]], DatasetValidationReport]:
    """
    Validate records according to dataset_type-specific profile.

    Returns (valid_records, report) with structured diagnostics.
    """
    profile = get_validation_profile(dataset_type)
    required = profile.get("required", [])
    any_of_required = profile.get("any_of_required", [])
    recommended = profile.get("recommended", [])

    report = DatasetValidationReport(dataset_type)
    report.records_received = len(records)
    report.duplicates_detected = duplicates_removed

    valid: List[Dict[str, Any]] = []
    seen_ids: set = set()

    for idx, raw in enumerate(records):
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        # Check amount
        has_amt, amt_field_or_msg = _has_amount(raw)
        if not has_amt:
            # Determine if amount field present but invalid vs missing
            errors.append({
                "field": "amount",
                "code": "INVALID_AMOUNT" if "Invalid" in amt_field_or_msg or "Zero" in amt_field_or_msg else "MISSING_AMOUNT",
                "message": amt_field_or_msg,
            })

        # Check timestamp
        has_ts, ts_msg = _has_timestamp(raw)
        if not has_ts:
            errors.append({"field": "timestamp", "code": "MISSING_TIMESTAMP", "message": ts_msg})
            # Also include string error for legacy validation_errors list
            report.validation_errors.append(f"[row {idx}] {ts_msg}")

        # Check any_of identifier
        has_id, id_msg = _has_identifier(raw, any_of_required)
        if not has_id:
            errors.append({"field": "identifier", "code": "MISSING_IDENTIFIER", "message": id_msg})
            report.validation_errors.append(f"[row {idx}] {id_msg}")

        # Check other required fields (like they are already amount/timestamp, but profile may have more)
        for field in required:
            if field in ("amount", "timestamp"):
                continue  # already checked via flexible amount/timestamp
            val = raw.get(field)
            if val is None or str(val).strip() == "":
                # For required fields that are not amount/timestamp, error
                errors.append({"field": field, "code": "MISSING_FIELD", "message": f"Missing {field}"})
                report.validation_errors.append(f"[row {idx}] Missing {field}")

        # Recommended fields warnings (not errors)
        for field in recommended:
            val = raw.get(field)
            if val is None or str(val).strip() == "":
                warnings.append({"field": field, "code": "MISSING_RECOMMENDED", "message": f"Missing recommended {field}"})

        # Duplicate detection based on primary identifier
        primary_id = None
        for fid in any_of_required:
            if raw.get(fid):
                primary_id = str(raw.get(fid))
                break
        if primary_id and primary_id in seen_ids:
            errors.append({"field": "duplicate", "code": "DUPLICATE", "message": f"Duplicate {primary_id}"})
            report.duplicates_detected += 1
            report.validation_errors.append(f"[row {idx}] Duplicate {primary_id}")
        elif primary_id:
            seen_ids.add(primary_id)

        # Build diagnostics
        if errors:
            report.records_invalid += 1
            for e in errors:
                # Add to flat validation_errors for backward compat
                if e["code"] not in ("MISSING_RECOMMENDED",):
                    report.validation_errors.append(f"[row {idx}] {e['field']}: {e['message']}")
            report.diagnostics.append({
                "row": idx,
                "valid": False,
                "errors": errors,
                "warnings": warnings,
            })
        else:
            report.records_valid += 1
            # Normalize record for downstream: ensure _raw preserved, ensure timestamp/amount canonical
            # Keep original record but also ensure Dedup key
            valid.append(raw)
            if warnings:
                report.diagnostics.append({"row": idx, "valid": True, "errors": [], "warnings": warnings})
                for w in warnings:
                    report.warnings.append(f"[row {idx}] {w['field']}: {w['message']}")
            else:
                report.diagnostics.append({"row": idx, "valid": True, "errors": [], "warnings": []})

    logger.info(
        "Dataset validation (%s): %d received, %d valid, %d invalid, %d duplicates",
        dataset_type, report.records_received, report.records_valid, report.records_invalid, report.duplicates_detected,
    )
    return valid, report
