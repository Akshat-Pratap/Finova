"""Finova — Data Normalizer.

Converts various raw schemas into Finova canonical Pydantic models.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.models.transaction import Transaction, PaymentMethod, PaymentStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank_transaction import BankTransaction
from app.models.settlement import Settlement, SettlementStatus
from app.utils.dates import parse_date
from app.utils.amounts import to_decimal

logger = logging.getLogger(__name__)


class NormalizationResult:
    def __init__(self):
        self.records: list = []
        self.errors: List[str] = []
        self.normalized: int = 0
        self.failed: int = 0


def normalize_transactions(
    records: List[Dict],
    processing_run_id: str,
    organization_id: str = "org_default",
    dataset_id: Optional[str] = None,
) -> Tuple[List[Transaction], List[str]]:
    """Normalize raw dicts into Transaction models."""
    normalized: List[Transaction] = []
    errors: List[str] = []

    for raw in records:
        try:
            txn = _normalize_transaction(raw, processing_run_id, organization_id, dataset_id)
            normalized.append(txn)
        except Exception as exc:
            errors.append(f"Transaction normalization failed: {exc} | data={raw}")
            logger.debug("Failed to normalize transaction: %s | %s", exc, raw)

    logger.info("Normalized %d/%d transactions", len(normalized), len(records))
    return normalized, errors


def normalize_invoices(
    records: List[Dict],
    processing_run_id: str,
    organization_id: str = "org_default",
) -> Tuple[List[Invoice], List[str]]:
    """Normalize raw dicts into Invoice models."""
    normalized: List[Invoice] = []
    errors: List[str] = []

    for raw in records:
        try:
            inv = _normalize_invoice(raw, processing_run_id, organization_id)
            normalized.append(inv)
        except Exception as exc:
            errors.append(f"Invoice normalization failed: {exc}")

    return normalized, errors


def normalize_bank_transactions(
    records: List[Dict],
    processing_run_id: str,
    organization_id: str = "org_default",
) -> Tuple[List[BankTransaction], List[str]]:
    normalized: List[BankTransaction] = []
    errors: List[str] = []

    for raw in records:
        try:
            bank = _normalize_bank_transaction(raw, processing_run_id, organization_id)
            normalized.append(bank)
        except Exception as exc:
            errors.append(f"Bank transaction normalization failed: {exc}")

    return normalized, errors


def normalize_settlements(
    records: List[Dict],
    processing_run_id: str,
    organization_id: str = "org_default",
) -> Tuple[List[Settlement], List[str]]:
    normalized: List[Settlement] = []
    errors: List[str] = []

    for raw in records:
        try:
            s = _normalize_settlement(raw, processing_run_id, organization_id)
            normalized.append(s)
        except Exception as exc:
            errors.append(f"Settlement normalization failed: {exc}")

    return normalized, errors


# ---------------------------------------------------------------------------
# Internal normalizers
# ---------------------------------------------------------------------------

def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return parse_date(str(value))


def _normalize_transaction(
    raw: Dict,
    run_id: str,
    organization_id: str = "org_default",
    dataset_id: Optional[str] = None,
) -> Transaction:
    ts = _parse_dt(raw.get("timestamp") or raw.get("date") or raw.get("created_at")) or datetime.utcnow()

    return Transaction(
        transaction_id=str(raw.get("transaction_id") or uuid.uuid4().hex),
        order_id=raw.get("order_id"),
        customer_id=str(raw.get("customer_id", "UNKNOWN")),
        amount=to_decimal(raw.get("amount")) or Decimal("0"),
        currency=str(raw.get("currency", "INR")),
        payment_status=_safe_enum(PaymentStatus, raw.get("payment_status"), PaymentStatus.CAPTURED),
        payment_method=_safe_enum(PaymentMethod, raw.get("payment_method"), PaymentMethod.UNKNOWN),
        timestamp=ts,
        reference_id=raw.get("reference_id") or raw.get("reference"),
        invoice_id=raw.get("invoice_id"),
        description=raw.get("description"),
        processing_run_id=run_id,
        organization_id=organization_id,
        dataset_id=dataset_id,
        ground_truth_status=raw.get("ground_truth_status"),
        source="uploaded" if not raw.get("ground_truth_status") else "synthetic",
    )


def _normalize_invoice(raw: Dict, run_id: str, organization_id: str = "org_default") -> Invoice:
    date = _parse_dt(raw.get("date") or raw.get("created_at")) or datetime.utcnow()
    due_date = _parse_dt(raw.get("due_date"))

    inv_amount = to_decimal(raw.get("invoice_amount") or raw.get("amount")) or Decimal("0")
    tax = to_decimal(raw.get("tax")) or Decimal("0")
    total = to_decimal(raw.get("total_amount")) or (inv_amount + tax)

    return Invoice(
        invoice_id=str(raw.get("invoice_id") or uuid.uuid4().hex),
        customer_id=str(raw.get("customer_id", "UNKNOWN")),
        invoice_amount=inv_amount,
        tax=tax,
        total_amount=total,
        date=date,
        due_date=due_date,
        status=_safe_enum(InvoiceStatus, raw.get("status"), InvoiceStatus.UNPAID),
        description=raw.get("description"),
        processing_run_id=run_id,
        organization_id=organization_id,
    )


def _normalize_bank_transaction(raw: Dict, run_id: str, organization_id: str = "org_default") -> BankTransaction:
    date = _parse_dt(raw.get("date") or raw.get("timestamp")) or datetime.utcnow()
    return BankTransaction(
        bank_transaction_id=str(raw.get("bank_transaction_id") or uuid.uuid4().hex),
        date=date,
        amount=to_decimal(raw.get("amount")) or Decimal("0"),
        description=raw.get("description"),
        reference=raw.get("reference") or raw.get("reference_id"),
        account=raw.get("account"),
        processing_run_id=run_id,
        organization_id=organization_id,
    )


def _normalize_settlement(raw: Dict, run_id: str, organization_id: str = "org_default") -> Settlement:
    date = _parse_dt(raw.get("settlement_date") or raw.get("date")) or datetime.utcnow()
    gross = to_decimal(raw.get("gross_amount") or raw.get("amount")) or Decimal("0")
    fees = to_decimal(raw.get("fees")) or Decimal("0")
    tax = to_decimal(raw.get("tax")) or Decimal("0")
    net = to_decimal(raw.get("net_amount")) or (gross - fees - tax)

    return Settlement(
        settlement_id=str(raw.get("settlement_id") or uuid.uuid4().hex),
        transaction_id=str(raw.get("transaction_id", "")),
        gross_amount=gross,
        fees=fees,
        tax=tax,
        net_amount=net,
        settlement_date=date,
        status=_safe_enum(SettlementStatus, raw.get("status"), SettlementStatus.PROCESSED),
        processing_run_id=run_id,
        organization_id=organization_id,
    )



def _safe_enum(enum_class, value, default):
    """Safely parse an enum value, returning default on failure."""
    if value is None:
        return default
    try:
        return enum_class(str(value).lower())
    except ValueError:
        return default
