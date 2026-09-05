"""Finova — Dataset Model."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetType(str, Enum):
    """Financial dataset type for generic reconciliation."""
    BANK_TRANSACTION = "BANK_TRANSACTION"
    INVOICE = "INVOICE"
    PAYMENT = "PAYMENT"
    SETTLEMENT = "SETTLEMENT"
    LEDGER = "LEDGER"
    GENERIC_TRANSACTION = "GENERIC_TRANSACTION"
    UNKNOWN = "UNKNOWN"


# Compatibility matrix for counterpart discovery
# Each type maps to set of compatible counterpart types
COMPATIBLE_TYPES: Dict[str, set] = {
    DatasetType.BANK_TRANSACTION: {
        DatasetType.INVOICE,
        DatasetType.PAYMENT,
        DatasetType.SETTLEMENT,
        DatasetType.LEDGER,
        DatasetType.GENERIC_TRANSACTION,
        DatasetType.BANK_TRANSACTION,  # allow same-type for cases like ledger vs ledger
    },
    DatasetType.INVOICE: {
        DatasetType.BANK_TRANSACTION,
        DatasetType.PAYMENT,
        DatasetType.SETTLEMENT,
        DatasetType.LEDGER,
        DatasetType.GENERIC_TRANSACTION,
    },
    DatasetType.PAYMENT: {
        DatasetType.BANK_TRANSACTION,
        DatasetType.INVOICE,
        DatasetType.SETTLEMENT,
        DatasetType.LEDGER,
        DatasetType.GENERIC_TRANSACTION,
    },
    DatasetType.SETTLEMENT: {
        DatasetType.BANK_TRANSACTION,
        DatasetType.INVOICE,
        DatasetType.PAYMENT,
        DatasetType.LEDGER,
        DatasetType.GENERIC_TRANSACTION,
    },
    DatasetType.LEDGER: {
        DatasetType.BANK_TRANSACTION,
        DatasetType.INVOICE,
        DatasetType.PAYMENT,
        DatasetType.SETTLEMENT,
        DatasetType.GENERIC_TRANSACTION,
    },
    DatasetType.GENERIC_TRANSACTION: {
        DatasetType.BANK_TRANSACTION,
        DatasetType.INVOICE,
        DatasetType.PAYMENT,
        DatasetType.SETTLEMENT,
        DatasetType.LEDGER,
        DatasetType.GENERIC_TRANSACTION,
    },
    DatasetType.UNKNOWN: {
        DatasetType.BANK_TRANSACTION,
        DatasetType.INVOICE,
        DatasetType.PAYMENT,
        DatasetType.SETTLEMENT,
        DatasetType.LEDGER,
        DatasetType.GENERIC_TRANSACTION,
        DatasetType.UNKNOWN,
    },
}


def get_compatible_types(dataset_type: str) -> set:
    """Return set of compatible counterpart types for a given type."""
    return COMPATIBLE_TYPES.get(dataset_type, COMPATIBLE_TYPES[DatasetType.UNKNOWN])


def infer_dataset_type(
    column_mapping: Dict[str, str],
    raw_columns: Optional[List[str]] = None,
    raw_sample: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Infer dataset type from semantic mapping and raw schema.
    Priority:
    1. Explicit canonical targets in mapping
    2. Raw column name heuristics (never filename)
    3. Fallback to GENERIC_TRANSACTION if financial data present
    """
    canonical_targets = set(column_mapping.values()) if column_mapping else set()
    # Also consider keys that were not mapped but look like canonical? Check raw columns
    raw_cols_lower = [c.lower().strip() for c in (raw_columns or [])]
    raw_joined = " ".join(raw_cols_lower)

    # Priority 1: explicit canonical signals
    if "invoice_id" in canonical_targets:
        return DatasetType.INVOICE
    if "bank_transaction_id" in canonical_targets:
        return DatasetType.BANK_TRANSACTION
    if "settlement_id" in canonical_targets:
        return DatasetType.SETTLEMENT
    if "payment_id" in canonical_targets:
        return DatasetType.PAYMENT
    # Check for settlement-specific amount fields
    if any(k in canonical_targets for k in ("gross_amount", "net_amount", "settlement_id")):
        # If settlement fields present without bank/invoice, treat as SETTLEMENT
        if "transaction_id" not in canonical_targets or "settlement" in raw_joined:
            return DatasetType.SETTLEMENT

    # Priority 2: raw column heuristics (safe, not filename)
    if "invoice" in raw_joined:
        # Could be invoice file
        if any("invoice" in c for c in raw_cols_lower):
            return DatasetType.INVOICE
    if "bank" in raw_joined or "statement" in raw_joined:
        return DatasetType.BANK_TRANSACTION
    if "payment" in raw_joined and "invoice" not in raw_joined:
        return DatasetType.PAYMENT
    if "settlement" in raw_joined or "payout" in raw_joined:
        return DatasetType.SETTLEMENT
    if "ledger" in raw_joined:
        return DatasetType.LEDGER

    # Priority 3: fallback based on available canonical fields
    if "transaction_id" in canonical_targets:
        # Transaction-centric - default to BANK_TRANSACTION for generic financial CSVs
        # Distinguish PAYMENT only if strong payment signals and no bank context
        if any(k in canonical_targets for k in ("payment_method", "payment_status")) and "invoice_id" not in canonical_targets:
            # Could be payment, but bank also has these - keep BANK for broad compatibility
            return DatasetType.BANK_TRANSACTION
        return DatasetType.BANK_TRANSACTION

    if canonical_targets:
        # Has financial fields but no clear ID -> generic
        has_amount = "amount" in canonical_targets or "invoice_amount" in canonical_targets or "total_amount" in canonical_targets
        has_date = "timestamp" in canonical_targets
        if has_amount and has_date:
            return DatasetType.GENERIC_TRANSACTION

    return DatasetType.UNKNOWN


# Validation profiles per dataset type
VALIDATION_PROFILES: Dict[str, Dict[str, List[str]]] = {
    DatasetType.BANK_TRANSACTION: {
        "required": ["amount", "timestamp"],
        # transaction_id or bank_transaction_id at least one
        "any_of_required": ["transaction_id", "bank_transaction_id"],
        "recommended": ["reference_id", "customer_id", "description", "currency"],
    },
    DatasetType.INVOICE: {
        "required": ["amount", "timestamp"],
        "any_of_required": ["invoice_id"],
        "recommended": ["reference_id", "customer_id", "description", "currency", "status"],
    },
    DatasetType.PAYMENT: {
        "required": ["amount", "timestamp"],
        "any_of_required": ["transaction_id", "payment_id", "reference_id"],
        "recommended": ["customer_id", "description", "currency"],
    },
    DatasetType.SETTLEMENT: {
        "required": ["amount", "timestamp"],
        "any_of_required": ["settlement_id", "reference_id", "transaction_id"],
        "recommended": ["customer_id", "description", "currency"],
    },
    DatasetType.LEDGER: {
        "required": ["amount", "timestamp"],
        "any_of_required": ["transaction_id", "reference_id", "invoice_id", "bank_transaction_id"],
        "recommended": ["customer_id", "description", "currency"],
    },
    DatasetType.GENERIC_TRANSACTION: {
        "required": ["amount", "timestamp"],
        "any_of_required": ["transaction_id", "invoice_id", "bank_transaction_id", "reference_id", "payment_id", "settlement_id"],
        "recommended": ["customer_id", "description", "currency"],
    },
    DatasetType.UNKNOWN: {
        "required": ["amount"],
        "any_of_required": ["transaction_id", "invoice_id", "reference_id"],
        "recommended": ["customer_id", "description"],
    },
}


def get_validation_profile(dataset_type: str) -> Dict[str, List[str]]:
    """Return validation profile for dataset type."""
    return VALIDATION_PROFILES.get(dataset_type, VALIDATION_PROFILES[DatasetType.UNKNOWN])


class DatasetStatus(str, Enum):
    UPLOADED = "UPLOADED"
    MAPPED = "MAPPED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    READY_FOR_RECONCILIATION = "READY_FOR_RECONCILIATION"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Dataset(BaseModel):
    """Uploaded financial dataset tracking entity."""

    dataset_id: str = Field(default_factory=lambda: f"ds_{uuid.uuid4().hex[:12]}")
    organization_id: str
    filename: str
    source_type: str = "csv"  # csv, json, bank_statement, razorpay, synthetic
    dataset_type: str = DatasetType.UNKNOWN  # financial type (BANK_TRANSACTION, INVOICE, etc.)
    record_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    column_mapping: Dict[str, str] = Field(default_factory=dict)
    canonical_fields: List[str] = Field(default_factory=list)  # available canonical fields
    required_fields: List[str] = Field(default_factory=list)  # required for this type
    uploaded_by: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    validated_at: Optional[datetime] = None
    processing_status: DatasetStatus = DatasetStatus.UPLOADED
    processing_run_id: Optional[str] = None
    validation_errors: List[str] = Field(default_factory=list)
    validation_diagnostics: List[Dict[str, Any]] = Field(default_factory=list)  # structured per-row diagnostics
    raw_sample: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
