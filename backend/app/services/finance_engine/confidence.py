"""Finova — Confidence Scoring Engine.

Computes a transparent, weighted confidence score for each match.
Weights are configurable via app settings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Optional

from app.core.config import settings
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.bank_transaction import BankTransaction
from app.models.reconciliation import ConfidenceSignals
from app.services.finance_engine.fuzzy_matcher import (
    reference_similarity,
    customer_name_similarity,
    description_similarity,
    REFERENCE_FUZZY_THRESHOLD,
    CUSTOMER_FUZZY_THRESHOLD,
)
from app.utils.dates import days_between


@dataclass
class ScoringResult:
    """Full confidence scoring result with signal breakdown."""
    confidence: float
    signals: ConfidenceSignals
    score_breakdown: Dict[str, float] = field(default_factory=dict)


def compute_confidence(
    txn: Transaction,
    invoice: Optional[Invoice] = None,
    bank_txn: Optional[BankTransaction] = None,
    amount_difference: Optional[Decimal] = None,
    date_difference_days: Optional[int] = None,
    description_sim: float = 0.0,
) -> ScoringResult:
    """
    Compute a weighted confidence score.

    Weights (from config):
        reference_match      30%
        amount_match         30%
        customer_match       15%
        date_proximity       10%
        invoice_match        10%
        description_sim       5%
    """
    signals = ConfidenceSignals()
    breakdown: Dict[str, float] = {}

    # ── Reference ──────────────────────────────────────────────────────────
    ref_score = 0.0
    bank_ref = bank_txn.reference if bank_txn else None
    if txn.reference_id and bank_ref:
        if txn.reference_id == bank_ref:
            ref_score = 1.0
            signals.reference_match = True
        else:
            sim = reference_similarity(txn.reference_id, bank_ref)
            if sim >= REFERENCE_FUZZY_THRESHOLD:
                ref_score = sim * 0.9  # Slightly penalised for fuzzy
                signals.reference_match = True
            else:
                ref_score = sim * 0.3
    elif txn.reference_id is None:
        ref_score = 0.0  # No reference is a penalty
    breakdown["reference"] = ref_score * settings.weight_reference

    # ── Amount ─────────────────────────────────────────────────────────────
    amount_score = 0.0
    if invoice:
        diff = abs(txn.amount - invoice.invoice_amount)
        signals.amount_difference = diff
        if diff == Decimal("0"):
            amount_score = 1.0
            signals.amount_match = True
        elif diff <= Decimal("50"):
            amount_score = 0.85
        elif diff / invoice.invoice_amount < Decimal("0.05"):
            amount_score = 0.70
        elif diff / invoice.invoice_amount < Decimal("0.10"):
            amount_score = 0.50
        else:
            amount_score = max(0.0, float(1 - diff / invoice.invoice_amount))
    elif amount_difference is not None:
        if amount_difference == Decimal("0"):
            amount_score = 1.0
            signals.amount_match = True
        elif amount_difference < Decimal("100"):
            amount_score = 0.80
        else:
            amount_score = 0.3
    breakdown["amount"] = amount_score * settings.weight_amount

    # ── Customer ───────────────────────────────────────────────────────────
    cust_score = 0.0
    if invoice and txn.customer_id == invoice.customer_id:
        cust_score = 1.0
        signals.customer_match = True
    elif invoice:
        # IDs don't match; try fuzzy name match if we had names
        cust_score = 0.0
    breakdown["customer"] = cust_score * settings.weight_customer

    # ── Date ───────────────────────────────────────────────────────────────
    date_score = 0.0
    if date_difference_days is not None:
        signals.date_difference_days = date_difference_days
        if date_difference_days == 0:
            date_score = 1.0
            signals.date_match = True
        elif date_difference_days <= 1:
            date_score = 0.90
            signals.date_match = True
        elif date_difference_days <= 3:
            date_score = 0.75
        elif date_difference_days <= 7:
            date_score = 0.50
        else:
            date_score = max(0.0, 1 - date_difference_days / 30)
    elif invoice:
        diff_days = days_between(txn.timestamp, invoice.date)
        signals.date_difference_days = diff_days
        if diff_days <= settings.date_tolerance_days:
            date_score = 0.80
            signals.date_match = True
        elif diff_days <= 7:
            date_score = 0.60
        elif diff_days <= 30:
            date_score = 0.40
    breakdown["date"] = date_score * settings.weight_date

    # ── Invoice match ──────────────────────────────────────────────────────
    inv_score = 0.0
    if invoice:
        if txn.invoice_id and txn.invoice_id == invoice.invoice_id:
            inv_score = 1.0
            signals.invoice_match = True
        elif txn.invoice_id:
            inv_score = 0.0
        else:
            inv_score = 0.5  # No invoice_id on transaction, but we found a plausible match
    breakdown["invoice"] = inv_score * settings.weight_invoice

    # ── Description ────────────────────────────────────────────────────────
    desc_score = description_sim
    signals.description_similarity = desc_score
    breakdown["description"] = desc_score * settings.weight_description

    # ── Total ──────────────────────────────────────────────────────────────
    confidence = sum(breakdown.values())
    confidence = round(min(max(confidence, 0.0), 1.0), 4)

    return ScoringResult(
        confidence=confidence,
        signals=signals,
        score_breakdown=breakdown,
    )
