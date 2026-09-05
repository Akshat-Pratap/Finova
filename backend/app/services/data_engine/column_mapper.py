"""Finova — Column Mapping & Schema Detection.

Automatically detects column semantics and applies custom mappings from external sources.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Standard canonical fields for financial transactions — extended for generic types
# Order matters: reference_id before payment_id to avoid "Payment Ref" misclassification
CANONICAL_FIELDS = {
    "transaction_id": ["transaction_id", "txn_id", "trans_id", "txnid", "record_id"],
    "bank_transaction_id": ["bank_transaction_id", "bank_txn_id", "statement_id", "bank_transaction", "bank_txn"],
    "invoice_id": ["invoice_id", "inv_id", "bill_id", "invoice_num", "invoice_number", "bill_number", "invoice_no"],
    "reference_id": ["reference_id", "reference", "ref_id", "ref", "utr", "bank_ref", "payment_ref", "rrn", "ref_num", "utr_number", "rrn_number", "payment_ref"],
    "payment_id": ["payment_id", "pay_id", "payment_transaction_id", "razorpay_payment_id"],
    "settlement_id": ["settlement_id", "settlement_ref", "payout_id", "settle_id", "settlement_no", "payout_ref"],
    "customer_id": ["customer_id", "cust_id", "customer", "payer", "client_id", "client", "buyer", "customer_name", "payer_name", "client_name", "buyer_name"],
    "invoice_amount": ["invoice_amount", "inv_amount", "bill_amount", "invoiced_amount"],
    "total_amount": ["total_amount", "grand_total", "invoice_total_amount"],
    "gross_amount": ["settlement_gross", "gross_total"],
    "net_amount": ["settlement_net", "net_payout", "payout_amount"],
    "amount": ["amount", "txn_amount", "paid_amount", "amt", "value", "total", "amount_paid", "transaction_amount", "gross_amount", "net_amount"],
    "fees": ["fees", "fee", "charges", "commission", "gateway_fee", "deduction"],
    "tax": ["tax", "gst", "vat", "tax_amount", "gst_amount"],
    "currency": ["currency", "curr", "currency_code", "ccy"],
    "timestamp": ["timestamp", "date", "created_at", "txn_date", "payment_date", "time", "date_time", "trans_date", "invoice_date", "settlement_date", "bank_date", "transaction_date", "posting_date", "value_date"],
    "description": ["description", "desc", "narration", "remarks", "memo", "notes", "details", "particulars", "narrative"],
    "order_id": ["order_id", "order_number", "order_ref", "order_no", "order_num"],
    "payment_method": ["payment_method", "method", "mode", "channel", "pay_mode"],
    "payment_status": ["payment_status", "status", "state", "tx_status", "invoice_status", "payment_state"],
}


def detect_column_mapping(columns: List[str]) -> Dict[str, str]:
    """
    Given a list of column names from a CSV or JSON file, auto-detect
    which raw column maps to which canonical target field.

    Returns mapping: { "raw_column_name": "canonical_field_name" }
    """
    detected_mapping: Dict[str, str] = {}
    assigned_targets = set()

    for col in columns:
        col_clean = re.sub(r"[_\s\-]+", "_", col.strip().lower())
        best_match = None

        # Check exact and substring aliases
        for canonical, aliases in CANONICAL_FIELDS.items():
            if canonical in assigned_targets:
                continue

            for alias in aliases:
                if col_clean == alias or col_clean == alias.replace("_", ""):
                    best_match = canonical
                    break

            if best_match:
                break

        if not best_match:
            # Substring heuristic
            for canonical, aliases in CANONICAL_FIELDS.items():
                if canonical in assigned_targets:
                    continue
                if canonical in col_clean or any(a in col_clean for a in aliases):
                    best_match = canonical
                    break

        if best_match:
            detected_mapping[col] = best_match
            assigned_targets.add(best_match)

    return detected_mapping


def apply_column_mapping(
    records: List[Dict[str, Any]],
    mapping: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Transform raw records by renaming mapped columns to canonical fields,
    while preserving original keys in a raw metadata attribute for complete data provenance.
    """
    mapped_records = []
    for row in records:
        mapped_row: Dict[str, Any] = {}
        # Keep original raw record for audit provenance
        mapped_row["_raw"] = row.copy()

        for raw_col, value in row.items():
            canonical_col = mapping.get(raw_col, raw_col)
            mapped_row[canonical_col] = value

        mapped_records.append(mapped_row)
    return mapped_records
