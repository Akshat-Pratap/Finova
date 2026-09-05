"""Finova — Exact (Deterministic) Matcher.

Performs exact field-by-field matching of transactions against invoices,
bank records, and settlements. Returns structured match evidence.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.bank_transaction import BankTransaction
from app.models.settlement import Settlement
from app.utils.amounts import amounts_match
from app.utils.dates import days_between

logger = logging.getLogger(__name__)


class MatchEvidence:
    """Evidence collected during matching."""

    def __init__(self):
        self.reference_exact: bool = False
        self.reference_fuzzy: float = 0.0
        self.amount_exact: bool = False
        self.amount_difference: Optional[Decimal] = None
        self.customer_exact: bool = False
        self.customer_fuzzy: float = 0.0
        self.date_difference_days: Optional[int] = None
        self.date_within_tolerance: bool = False
        self.invoice_id_match: bool = False
        self.description_similarity: float = 0.0
        self.matched_invoice_id: Optional[str] = None
        self.matched_bank_id: Optional[str] = None
        self.matched_settlement_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "reference_exact": self.reference_exact,
            "reference_fuzzy_score": self.reference_fuzzy,
            "amount_exact": self.amount_exact,
            "amount_difference": float(self.amount_difference) if self.amount_difference is not None else None,
            "customer_exact": self.customer_exact,
            "customer_fuzzy_score": self.customer_fuzzy,
            "date_difference_days": self.date_difference_days,
            "date_within_tolerance": self.date_within_tolerance,
            "invoice_id_match": self.invoice_id_match,
            "description_similarity": self.description_similarity,
        }


def match_transaction_to_invoice(
    txn: Transaction,
    invoices: List[Invoice],
    date_tolerance_days: int = 3,
) -> Tuple[Optional[Invoice], MatchEvidence]:
    """
    Find the best matching invoice for a transaction.

    Returns (best_invoice, evidence) or (None, evidence).
    """
    evidence = MatchEvidence()
    best_invoice: Optional[Invoice] = None
    best_score = -1.0

    for inv in invoices:
        score = 0.0

        # Invoice ID match (strongest signal)
        if txn.invoice_id and txn.invoice_id == inv.invoice_id:
            score += 3.0
            evidence.invoice_id_match = True

        # Customer match
        if txn.customer_id == inv.customer_id:
            score += 2.0
            evidence.customer_exact = True

        # Amount match
        if txn.amount == inv.invoice_amount or txn.amount == inv.total_amount:
            score += 2.0
            evidence.amount_exact = True

        if score > best_score:
            best_score = score
            best_invoice = inv
            if score >= 7.0:
                break

    if best_invoice:
        # Populate evidence for best match
        evidence.matched_invoice_id = best_invoice.invoice_id
        evidence.amount_difference = abs(txn.amount - best_invoice.invoice_amount)
        evidence.date_difference_days = days_between(txn.timestamp, best_invoice.date)
        evidence.date_within_tolerance = evidence.date_difference_days <= date_tolerance_days

    return best_invoice, evidence


def match_transaction_to_bank(
    txn: Transaction,
    bank_transactions: List[BankTransaction],
    date_tolerance_days: int = 3,
    amount_tolerance: Decimal = Decimal("50"),
) -> Tuple[Optional[BankTransaction], MatchEvidence]:
    """
    Find the best bank transaction match.

    Prioritizes reference ID then amount + date proximity.
    """
    evidence = MatchEvidence()
    best_bank: Optional[BankTransaction] = None
    best_score = -1.0

    for bank in bank_transactions:
        score = 0.0

        # Reference match (strongest signal)
        if txn.reference_id and bank.reference and txn.reference_id == bank.reference:
            score += 5.0
            evidence.reference_exact = True

        # Amount proximity
        diff = abs(txn.amount - bank.amount)
        if diff == Decimal("0"):
            score += 3.0
            evidence.amount_exact = True
        elif diff <= amount_tolerance:
            score += 1.0

        # Date proximity
        date_diff = days_between(txn.timestamp, bank.date)
        if date_diff == 0:
            score += 2.0
        elif date_diff <= date_tolerance_days:
            score += 1.0

        if score > best_score and score > 0:
            best_score = score
            best_bank = bank
            if score >= 10.0:
                break

    if best_bank:
        evidence.matched_bank_id = best_bank.bank_transaction_id
        evidence.amount_difference = abs(txn.amount - best_bank.amount)
        evidence.date_difference_days = days_between(txn.timestamp, best_bank.date)
        evidence.date_within_tolerance = (evidence.date_difference_days or 999) <= date_tolerance_days

    return best_bank, evidence


def match_transaction_to_settlement(
    txn: Transaction,
    settlements: List[Settlement],
) -> Tuple[Optional[Settlement], MatchEvidence]:
    """Match transaction to a settlement record."""
    evidence = MatchEvidence()

    for settlement in settlements:
        if settlement.transaction_id == txn.transaction_id:
            evidence.matched_settlement_id = settlement.settlement_id
            evidence.amount_difference = abs(txn.amount - settlement.gross_amount)
            return settlement, evidence

    return None, evidence
