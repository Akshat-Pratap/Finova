"""Finova — Reconciliation Pipeline.

Orchestrates the complete transaction reconciliation workflow:
Exact Match → Fuzzy Match → Confidence → Rules → Decision
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.models.invoice import Invoice
from app.models.bank_transaction import BankTransaction
from app.models.reconciliation import ReconciliationResult, ReconciliationStatus, ConfidenceSignals
from app.models.settlement import Settlement
from app.models.transaction import Transaction
from app.services.finance_engine.matcher import match_transaction_to_invoice, match_transaction_to_bank, match_transaction_to_settlement
from app.services.finance_engine.confidence import compute_confidence
from app.services.finance_engine.rules import evaluate_rules
from app.services.finance_engine.fee_detector import detect_fee_discrepancy
from app.services.finance_engine.fuzzy_matcher import reference_similarity, REFERENCE_FUZZY_THRESHOLD

logger = logging.getLogger(__name__)


def reconcile_transaction(
    txn: Transaction,
    invoices: List[Invoice],
    bank_transactions: List[BankTransaction],
    settlements: List[Settlement],
    processing_run_id: str,
    is_known_duplicate: bool = False,
) -> ReconciliationResult:
    """
    Full reconciliation pipeline for a single transaction.

    Returns a ReconciliationResult with status, confidence, and evidence.
    """
    # Short-circuit: known duplicate
    if is_known_duplicate:
        return ReconciliationResult(
            result_id=uuid.uuid4().hex,
            processing_run_id=processing_run_id,
            transaction_id=txn.transaction_id,
            customer_id=txn.customer_id,
            status=ReconciliationStatus.DUPLICATE,
            confidence=0.95,
            reason="Transaction flagged as duplicate based on reference ID, amount, and customer match.",
            signals=ConfidenceSignals(is_duplicate=True),
            expected_amount=txn.amount,
            actual_amount=txn.amount,
            difference=Decimal("0"),
            ground_truth_status=txn.ground_truth_status,
        )

    # Step 1: Match to invoice
    matched_invoice, inv_evidence = match_transaction_to_invoice(
        txn, invoices, settings.date_tolerance_days
    )

    # Step 2: Match to bank transaction
    matched_bank, bank_evidence = match_transaction_to_bank(
        txn, bank_transactions, settings.date_tolerance_days
    )

    # Step 3: Match to settlement
    matched_settlement, settle_evidence = match_transaction_to_settlement(txn, settlements)

    # Step 4: Compute confidence score
    date_diff = bank_evidence.date_difference_days or inv_evidence.date_difference_days
    amount_diff = bank_evidence.amount_difference or inv_evidence.amount_difference

    scoring = compute_confidence(
        txn=txn,
        invoice=matched_invoice,
        bank_txn=matched_bank,
        amount_difference=amount_diff,
        date_difference_days=date_diff,
    )

    # Step 5: Rule evaluation
    rule_eval = evaluate_rules(
        txn=txn,
        expected_amount=matched_invoice.invoice_amount if matched_invoice else None,
        actual_amount=txn.amount,
        settlement=matched_settlement,
        date_difference_days=date_diff,
    )

    # Apply rule-based confidence bonus
    confidence = min(scoring.confidence + rule_eval.confidence_bonus, 1.0)

    # Step 6: Fee discrepancy check
    is_fee, fee_explanation, fee_diff = detect_fee_discrepancy(txn, matched_settlement)
    scoring.signals.is_fee_explainable = is_fee

    # Step 7: Build amounts
    expected = matched_invoice.invoice_amount if matched_invoice else txn.amount
    actual = matched_bank.amount if matched_bank else txn.amount
    difference = abs(expected - actual)

    # Step 8: Determine status and reason
    status, reason = _determine_status(
        confidence=confidence,
        txn=txn,
        matched_invoice=matched_invoice,
        matched_bank=matched_bank,
        rule_eval=rule_eval,
        difference=difference,
        expected=expected,
    )

    result = ReconciliationResult(
        result_id=uuid.uuid4().hex,
        processing_run_id=processing_run_id,
        transaction_id=txn.transaction_id,
        invoice_id=matched_invoice.invoice_id if matched_invoice else None,
        bank_transaction_id=matched_bank.bank_transaction_id if matched_bank else None,
        settlement_id=matched_settlement.settlement_id if matched_settlement else None,
        customer_id=txn.customer_id,
        status=status,
        confidence=confidence,
        reason=reason,
        signals=scoring.signals,
        expected_amount=expected,
        actual_amount=actual,
        difference=difference,
        ground_truth_status=txn.ground_truth_status,
    )

    return result


def _determine_status(
    confidence: float,
    txn: Transaction,
    matched_invoice: Optional[Invoice],
    matched_bank: Optional[BankTransaction],
    rule_eval,
    difference: Decimal,
    expected: Decimal,
) -> Tuple[ReconciliationStatus, str]:
    """
    Apply the decision model.

    The decision is NOT solely based on confidence — it also considers
    the type of discrepancy and rule violations.
    """
    # No match found at all
    if not matched_invoice and not matched_bank:
        return (
            ReconciliationStatus.MANUAL_REVIEW,
            "No matching invoice or bank record found for this transaction.",
        )

    # Missing reference — harder to reconcile automatically
    if txn.reference_id is None:
        if confidence >= settings.auto_reconcile_threshold:
            # Still auto-reconcile if everything else is perfect
            return (
                ReconciliationStatus.MATCHED,
                f"Matched without reference (confidence {confidence:.0%}). "
                f"Customer and amount match confirmed.",
            )
        return (
            ReconciliationStatus.AI_REVIEW,
            "Missing reference ID — AI investigation required.",
        )

    # Large amount difference — never auto-reconcile
    if expected > 0 and difference / expected > Decimal("0.10"):
        return (
            ReconciliationStatus.AI_REVIEW,
            f"Amount discrepancy of {float(difference/expected)*100:.1f}% requires investigation.",
        )

    # High confidence → auto reconcile
    if confidence >= settings.auto_reconcile_threshold:
        return (
            ReconciliationStatus.MATCHED,
            _build_match_reason(matched_invoice, matched_bank, confidence),
        )

    # Medium confidence → AI investigation
    if confidence >= settings.ai_review_threshold:
        return (
            ReconciliationStatus.AI_REVIEW,
            f"Confidence {confidence:.0%} — AI investigation required.",
        )

    # Low confidence → manual review
    return (
        ReconciliationStatus.MANUAL_REVIEW,
        f"Confidence {confidence:.0%} — insufficient evidence for automated reconciliation.",
    )


def _build_match_reason(
    invoice: Optional[Invoice],
    bank: Optional[BankTransaction],
    confidence: float,
) -> str:
    parts = [f"Confidence: {confidence:.0%}."]
    if invoice:
        parts.append(f"Invoice {invoice.invoice_id} matched.")
    if bank:
        parts.append(f"Bank record {bank.bank_transaction_id} matched.")
    return " ".join(parts)


def reconcile_batch(
    transactions: List[Transaction],
    invoices: List[Invoice],
    bank_transactions: List[BankTransaction],
    settlements: List[Settlement],
    processing_run_id: str,
    duplicate_ids: Optional[Set[str]] = None,
) -> List[ReconciliationResult]:
    """Reconcile a complete batch of transactions."""
    if duplicate_ids is None:
        duplicate_ids = set()

    results: List[ReconciliationResult] = []
    logger.info(
        "Reconciling batch: %d transactions, %d invoices, %d bank records, %d settlements",
        len(transactions), len(invoices), len(bank_transactions), len(settlements),
    )

    for txn in transactions:
        is_dup = txn.transaction_id in duplicate_ids
        result = reconcile_transaction(
            txn=txn,
            invoices=invoices,
            bank_transactions=bank_transactions,
            settlements=settlements,
            processing_run_id=processing_run_id,
            is_known_duplicate=is_dup,
        )
        results.append(result)

    logger.info("Reconciliation complete. %d results.", len(results))
    return results
