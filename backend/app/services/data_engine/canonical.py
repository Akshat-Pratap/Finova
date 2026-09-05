"""Finova — Canonical Financial Record Normalization.

Converts any mapped dataset record (bank/invoice/payment/settlement/generic)
into a unified canonical representation for cross-source matching.

Canonical fields:
- record_id: primary identifier for the record (invoice_id, bank_transaction_id, etc.)
- reference: UTR/RRN/reference_id for matching
- amount: Decimal monetary value
- currency: 3-letter code
- date: datetime for temporal matching
- counterparty: customer_id/payer
- description: narration
- dataset_type, dataset_id, organization_id
- raw: original _raw for provenance
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.models.dataset import DatasetType
from app.utils.dates import parse_date
from app.utils.amounts import to_decimal

logger = logging.getLogger(__name__)


def normalize_to_canonical(
    mapped_records: List[Dict[str, Any]],
    dataset_type: str,
    organization_id: str = "org_default",
    dataset_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convert mapped records to canonical form."""
    canonical: List[Dict[str, Any]] = []

    for idx, raw in enumerate(mapped_records):
        try:
            rec = _record_to_canonical(raw, dataset_type, organization_id, dataset_id)
            if rec is not None:
                canonical.append(rec)
        except Exception as exc:
            logger.debug("Canonical normalization failed for row %d [%s]: %s", idx, dataset_type, exc)

    logger.info("Canonical normalization [%s]: %d/%d records", dataset_type, len(canonical), len(mapped_records))
    return canonical


def _record_to_canonical(
    raw: Dict[str, Any],
    dataset_type: str,
    organization_id: str,
    dataset_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    # Resolve record_id based on type
    record_id = None
    if dataset_type == DatasetType.INVOICE:
        record_id = raw.get("invoice_id") or raw.get("transaction_id") or raw.get("reference_id")
    elif dataset_type == DatasetType.BANK_TRANSACTION:
        record_id = raw.get("bank_transaction_id") or raw.get("transaction_id") or raw.get("reference_id")
    elif dataset_type == DatasetType.SETTLEMENT:
        record_id = raw.get("settlement_id") or raw.get("transaction_id") or raw.get("reference_id")
    elif dataset_type == DatasetType.PAYMENT:
        record_id = raw.get("payment_id") or raw.get("transaction_id") or raw.get("reference_id")
    else:
        # Generic: try any identifier
        for fid in ("transaction_id", "invoice_id", "bank_transaction_id", "settlement_id", "payment_id", "reference_id", "order_id"):
            if raw.get(fid):
                record_id = str(raw.get(fid))
                break

    if not record_id:
        # Fallback to generated id but mark as warning — still allow matching via reference
        record_id = f"GEN-{uuid.uuid4().hex[:8].upper()}"
        # Use reference as fallback if available
        if raw.get("reference_id"):
            record_id = str(raw.get("reference_id"))

    # Reference: try reference_id, reference, utr, rrn, ref
    reference = (
        raw.get("reference_id")
        or raw.get("reference")
        or raw.get("utr")
        or raw.get("rrn")
        or raw.get("ref")
        or raw.get("order_id")
    )
    if reference is not None:
        reference = str(reference).strip()
        if reference == "":
            reference = None

    # Amount: try multiple fields
    amount = None
    for field in ("amount", "invoice_amount", "total_amount", "gross_amount", "net_amount", "fees"):
        if raw.get(field) is not None and str(raw.get(field)).strip() != "":
            dec = to_decimal(raw.get(field))
            if dec is not None:
                amount = dec
                break
    if amount is None:
        # No valid amount -> skip record (will be counted as invalid upstream, but handle gracefully)
        return None

    # Currency
    currency = str(raw.get("currency") or raw.get("curr") or "INR").strip().upper()
    if len(currency) != 3:
        currency = "INR"

    # Date: parse timestamp/date variants
    date_val = raw.get("timestamp") or raw.get("date") or raw.get("created_at") or raw.get("invoice_date") or raw.get("settlement_date") or raw.get("payment_date")
    date_obj = None
    if date_val is not None:
        if isinstance(date_val, datetime):
            date_obj = date_val
        else:
            date_obj = parse_date(str(date_val))
    if date_obj is None:
        date_obj = datetime.utcnow()

    # Counterparty
    counterparty = (
        raw.get("customer_id")
        or raw.get("customer_name")
        or raw.get("payer")
        or raw.get("client_id")
        or raw.get("buyer")
        or "UNKNOWN"
    )
    counterparty = str(counterparty).strip() or "UNKNOWN"

    # Description
    description = raw.get("description") or raw.get("desc") or raw.get("narration") or raw.get("remarks") or ""

    # Build canonical
    canonical = {
        "record_id": str(record_id),
        "reference": reference,
        "amount": amount,
        "currency": currency,
        "date": date_obj,
        "counterparty": counterparty,
        "description": str(description) if description else "",
        "dataset_type": dataset_type,
        "dataset_id": dataset_id,
        "organization_id": organization_id,
        "_raw": raw.get("_raw", raw),
        # Preserve original mapped fields for audit
        "original": raw,
    }
    return canonical
