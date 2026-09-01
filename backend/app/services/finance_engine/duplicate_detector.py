"""Finova — Duplicate Detector.

Detects duplicate transactions using reference ID, amount, customer, and timestamp.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Set, Tuple

from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


def detect_duplicates(transactions: List[Transaction]) -> Tuple[List[Transaction], Set[str]]:
    """
    Identify duplicate transactions in a batch.

    Returns (deduplicated_list, set_of_duplicate_transaction_ids).

    Duplicate criteria:
    - Same reference_id AND same amount AND same customer_id → very high likelihood
    - Same amount AND same customer_id AND within 1 hour → possible duplicate
    """
    duplicate_ids: Set[str] = set()
    seen_refs: Dict[str, str] = {}       # reference_id → first txn_id
    seen_amount_cust: Dict[str, str] = {}  # (amount, customer_id, date) → first txn_id

    for txn in transactions:
        # Signal 1: Reference + Amount + Customer
        if txn.reference_id:
            ref_key = f"{txn.reference_id}|{txn.amount}|{txn.customer_id}"
            if ref_key in seen_refs:
                logger.debug(
                    "Duplicate detected: %s matches %s (ref+amount+customer)",
                    txn.transaction_id, seen_refs[ref_key],
                )
                duplicate_ids.add(txn.transaction_id)
                continue
            seen_refs[ref_key] = txn.transaction_id

        # Signal 2: Amount + Customer + Same day
        date_key = txn.timestamp.date().isoformat() if txn.timestamp else "unknown"
        ac_key = f"{txn.amount}|{txn.customer_id}|{date_key}"
        if ac_key in seen_amount_cust:
            # Only flag as duplicate if reference IDs are the same or both missing
            existing_ref = seen_amount_cust.get(ac_key + "_ref")
            if txn.reference_id == existing_ref or (not txn.reference_id and not existing_ref):
                logger.debug(
                    "Potential duplicate: %s (amount+customer+date)",
                    txn.transaction_id,
                )
                duplicate_ids.add(txn.transaction_id)
                continue

        seen_amount_cust[ac_key] = txn.transaction_id
        seen_amount_cust[ac_key + "_ref"] = txn.reference_id

    unique = [t for t in transactions if t.transaction_id not in duplicate_ids]
    logger.info(
        "Duplicate detection: %d duplicates found in %d transactions",
        len(duplicate_ids), len(transactions),
    )
    return unique, duplicate_ids
