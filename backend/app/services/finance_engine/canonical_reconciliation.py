"""Finova — Generic Canonical Reconciliation Engine.

Cross-source matching without requiring identical source-specific IDs.
Supports INVOICE ↔ BANK ↔ PAYMENT ↔ SETTLEMENT ↔ LEDGER ↔ GENERIC
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.models.reconciliation import ReconciliationResult, ReconciliationStatus, ConfidenceSignals
from app.utils.dates import days_between

logger = logging.getLogger(__name__)


def _amount_within_tolerance(a: Decimal, b: Decimal, tolerance_percent: Decimal = Decimal("0.05")) -> bool:
    """Check if amounts match within tolerance."""
    if a == b:
        return True
    if a == Decimal("0") or b == Decimal("0"):
        return False
    diff = abs(a - b)
    avg = (a + b) / 2
    # Use percentage of expected
    pct = diff / a if a != Decimal("0") else Decimal("1")
    return pct <= tolerance_percent


def _counterparty_similarity(a: str, b: str) -> float:
    """Simple counterparty similarity (0-1)."""
    if not a or not b or a == "UNKNOWN" or b == "UNKNOWN":
        return 0.0
    a_low = a.lower().strip()
    b_low = b.lower().strip()
    if a_low == b_low:
        return 1.0
    if a_low in b_low or b_low in a_low:
        return 0.7
    # Jaccard on tokens
    a_tokens = set(a_low.split())
    b_tokens = set(b_low.split())
    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return inter / union if union else 0.0


def _build_indexes(counterparts: List[Dict[str, Any]]) -> Tuple[Dict[str, List[Dict]], Dict[str, List[Dict]], Dict[str, List[Dict]]]:
    """Build fast lookup indexes for counterpart records."""
    by_ref: Dict[str, List[Dict]] = defaultdict(list)
    by_amount_currency: Dict[str, List[Dict]] = defaultdict(list)
    by_counterparty: Dict[str, List[Dict]] = defaultdict(list)

    for rec in counterparts:
        ref = rec.get("reference")
        if ref:
            by_ref[str(ref).strip().lower()].append(rec)
        # Amount+currency key
        amt = rec.get("amount")
        curr = rec.get("currency", "INR")
        if amt is not None:
            key = f"{amt}:{curr}"
            by_amount_currency[key].append(rec)
            # Also bucket by amount string for tolerance lookup? Keep exact for now
        cp = rec.get("counterparty", "").lower().strip()
        if cp and cp != "unknown":
            by_counterparty[cp].append(rec)

    return by_ref, by_amount_currency, by_counterparty


def reconcile_canonical_batch(
    source_records: List[Dict[str, Any]],
    counterpart_records: List[Dict[str, Any]],
    processing_run_id: str,
    organization_id: str = "org_default",
    source_dataset_id: Optional[str] = None,
    counterpart_dataset_id: Optional[str] = None,
    source_type: Optional[str] = None,
    counterpart_type: Optional[str] = None,
) -> List[ReconciliationResult]:
    """
    Reconcile source vs counterpart canonical records.

    Implements priority:
    PASS1: exact reference + exact amount + currency
    PASS2: exact reference + date tolerance + amount tolerance
    PASS3: exact amount + currency + counterparty similarity
    PASS4: fuzzy (handled via AI review)
    """
    results: List[ReconciliationResult] = []

    # Build indexes for counterpart
    by_ref, by_amt_curr, by_cp = _build_indexes(counterpart_records)
    # Track which counterpart records have been matched to detect counterpart-only
    matched_counterpart_ids = set()

    date_tolerance = getattr(settings, "date_tolerance_days", 3)
    fee_tolerance = Decimal(str(getattr(settings, "fee_tolerance_percent", 0.05)))
    # Use 0.02 for exact, fee_tolerance for amount discrepancy

    for src in source_records:
        src_ref = str(src.get("reference") or "").strip().lower() if src.get("reference") else None
        src_amt = src.get("amount")
        src_curr = src.get("currency", "INR")
        src_date = src.get("date")
        src_cp = src.get("counterparty", "UNKNOWN")

        best_match: Optional[Dict[str, Any]] = None
        match_status: Optional[str] = None
        confidence: float = 0.0
        expected = src_amt
        actual = None
        difference = Decimal("0")
        reason = ""
        signals = ConfidenceSignals()

        # PASS1: exact reference + exact amount + currency
        if src_ref and src_ref in by_ref:
            candidates = by_ref[src_ref]
            for cand in candidates:
                if cand.get("currency") != src_curr:
                    continue
                # Amount exact?
                if cand.get("amount") == src_amt:
                    best_match = cand
                    match_status = ReconciliationStatus.MATCHED
                    confidence = 0.95
                    actual = cand.get("amount")
                    difference = abs(expected - actual) if expected and actual else Decimal("0")
                    signals.reference_match = True
                    signals.amount_match = True
                    signals.customer_match = _counterparty_similarity(src_cp, cand.get("counterparty", "")) > 0.6
                    signals.date_match = days_between(src_date, cand.get("date")) <= date_tolerance if src_date and cand.get("date") else False
                    reason = f"Exact reference {src.get('reference')} + amount {src_amt} + currency {src_curr} matched."
                    break
                # Amount discrepancy check within fee tolerance
                elif _amount_within_tolerance(src_amt, cand.get("amount"), fee_tolerance):
                    best_match = cand
                    match_status = ReconciliationStatus.MISMATCH
                    confidence = 0.82
                    actual = cand.get("amount")
                    difference = abs(expected - actual)
                    signals.reference_match = True
                    signals.amount_match = False
                    signals.customer_match = _counterparty_similarity(src_cp, cand.get("counterparty", "")) > 0.5
                    reason = f"Reference {src.get('reference')} matched but amount differs {src_amt} vs {cand.get('amount')} (diff {difference}, within tolerance?)"
                    break
                else:
                    # Reference matched but amount off more than tolerance -> amount discrepancy exception
                    best_match = cand
                    match_status = ReconciliationStatus.MISMATCH
                    confidence = 0.78
                    actual = cand.get("amount")
                    difference = abs(expected - actual)
                    signals.reference_match = True
                    signals.amount_match = False
                    reason = f"Reference {src.get('reference')} matched but monetary value differs {src_amt} vs {cand.get('amount')} (diff {difference})."
                    break

        # PASS2: exact reference + date tolerance + amount tolerance (if not already matched)
        if not best_match and src_ref and src_ref in by_ref:
            candidates = by_ref[src_ref]
            for cand in candidates:
                if cand.get("currency") != src_curr:
                    continue
                date_ok = False
                if src_date and cand.get("date"):
                    date_ok = days_between(src_date, cand.get("date")) <= date_tolerance
                amt_ok = _amount_within_tolerance(src_amt, cand.get("amount"), Decimal("0.10"))
                if date_ok and amt_ok:
                    best_match = cand
                    match_status = ReconciliationStatus.MATCHED if cand.get("amount") == src_amt else ReconciliationStatus.MISMATCH
                    confidence = 0.88 if match_status == ReconciliationStatus.MATCHED else 0.75
                    actual = cand.get("amount")
                    difference = abs(expected - actual) if expected and actual else Decimal("0")
                    signals.reference_match = True
                    signals.amount_match = amt_ok
                    signals.date_match = date_ok
                    reason = f"Reference {src.get('reference')} matched with date tolerance {date_tolerance}d and amount tolerance."
                    break

        # PASS3: exact amount + currency + counterparty similarity (only when at least one side missing reference)
        if not best_match:
            # Only allow amount+counterparty matching if reference is missing or not comparable
            # If both have references and they differ, do NOT match on amount alone
            src_has_ref = bool(src_ref)
            key = f"{src_amt}:{src_curr}"
            candidates = by_amt_curr.get(key, [])
            best_cp_score = 0.0
            best_cp_candidate = None
            for cand in candidates:
                cand_ref = str(cand.get("reference") or "").strip().lower() if cand.get("reference") else None
                cand_has_ref = bool(cand_ref)
                # If both have references, they must be compatible (exact or one contains the other) to allow amount-only match
                if src_has_ref and cand_has_ref and src_ref != cand_ref:
                    # References differ - skip amount-only match, this prevents invoice-only vs bank-only false positives
                    continue
                score = _counterparty_similarity(src_cp, cand.get("counterparty", ""))
                if score > best_cp_score and score >= 0.7:
                    if src_date and cand.get("date") and days_between(src_date, cand.get("date")) > date_tolerance * 2:
                        continue
                    best_cp_score = score
                    best_cp_candidate = cand
            if best_cp_candidate:
                best_match = best_cp_candidate
                match_status = ReconciliationStatus.AI_REVIEW  # ambiguous, needs AI
                confidence = 0.68 + (best_cp_score * 0.15)
                actual = best_match.get("amount")
                difference = abs(expected - actual) if expected and actual else Decimal("0")
                signals.reference_match = False
                signals.amount_match = True
                signals.customer_match = True
                signals.description_similarity = best_cp_score
                reason = f"Amount {src_amt} + currency + counterparty {src_cp} matched (score {best_cp_score:.2f}) — AI review."

        # Final decision if still no match
        if not best_match:
            # No counterpart found
            match_status = ReconciliationStatus.MANUAL_REVIEW
            confidence = 0.35
            actual = None
            difference = Decimal("0")
            signals.reference_match = False
            signals.amount_match = False
            reason = f"No matching counterpart found for {src.get('record_id')} (ref {src.get('reference')}, amount {src_amt})."

            # Check currency mismatch as special case: if counterpart exists with same ref but different currency
            if src_ref and src_ref in by_ref:
                for cand in by_ref[src_ref]:
                    if cand.get("currency") != src_curr:
                        match_status = ReconciliationStatus.MISMATCH
                        confidence = 0.45
                        reason = f"Reference {src.get('reference')} matched but currency mismatch {src_curr} vs {cand.get('currency')}."
                        best_match = cand
                        actual = cand.get("amount")
                        difference = Decimal("0")
                        break
        else:
            # Mark counterpart as matched
            matched_counterpart_ids.add(best_match.get("record_id"))

        # Determine final status based on confidence if not already set
        if match_status is None:
            if confidence >= 0.90:
                match_status = ReconciliationStatus.MATCHED
            elif confidence >= 0.70:
                match_status = ReconciliationStatus.AI_REVIEW
            else:
                match_status = ReconciliationStatus.MANUAL_REVIEW

        # Build result
        result = ReconciliationResult(
            result_id=uuid.uuid4().hex,
            processing_run_id=processing_run_id,
            organization_id=organization_id,
            dataset_id=source_dataset_id,
            transaction_id=src.get("record_id") or f"SRC-{uuid.uuid4().hex[:8]}",
            customer_id=src.get("counterparty", "UNKNOWN"),
            status=match_status,
            confidence=confidence,
            reason=reason,
            signals=signals,
            expected_amount=expected,
            actual_amount=actual,
            difference=difference,
            ground_truth_status=src.get("ground_truth_status"),
        )
        # Attach counterpart linkage if matched
        if best_match:
            # Use generic fields to populate counterpart linkage
            if best_match.get("dataset_type") == "INVOICE" or "INV" in str(best_match.get("record_id", "")):
                result.invoice_id = best_match.get("record_id")
            elif best_match.get("dataset_type") == "BANK_TRANSACTION" or "BNK" in str(best_match.get("record_id", "")) or "TXN" in str(best_match.get("record_id", "")):
                result.bank_transaction_id = best_match.get("record_id")
            else:
                # Generic
                result.invoice_id = best_match.get("record_id") if best_match.get("dataset_type") == "INVOICE" else result.invoice_id
                result.bank_transaction_id = best_match.get("record_id") if best_match.get("dataset_type") != "INVOICE" else result.bank_transaction_id

        results.append(result)

    # Handle counterpart-only records (e.g., bank-only) as additional results? 
    # For now, we count them as MANUAL_REVIEW for counterpart side if needed for reporting.
    # But to avoid double counting, we can generate counterpart-only exceptions as separate results
    # if they were not matched.
    # Find unmatched counterpart records
    for cand in counterpart_records:
        if cand.get("record_id") not in matched_counterpart_ids:
            # This counterpart has no source match -> create a counterpart-only result
            # Only if it has reference or amount that should have matched but didn't
            # We create a MISSING-like result for reporting
            results.append(
                ReconciliationResult(
                    result_id=uuid.uuid4().hex,
                    processing_run_id=processing_run_id,
                    organization_id=organization_id,
                    dataset_id=counterpart_dataset_id,
                    transaction_id=cand.get("record_id"),
                    customer_id=cand.get("counterparty", "UNKNOWN"),
                    status=ReconciliationStatus.MISSING,
                    confidence=0.40,
                    reason=f"Counterpart record {cand.get('record_id')} (ref {cand.get('reference')}) has no matching source record.",
                    signals=ConfidenceSignals(reference_match=False, amount_match=False),
                    expected_amount=cand.get("amount"),
                    actual_amount=None,
                    difference=Decimal("0"),
                )
            )

    return results
