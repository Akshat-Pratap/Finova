"""Finova — Financial Rule Engine.

Applies configurable financial rules to determine if discrepancies
are explainable (fees, tax, partial payments, settlement delays).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from app.core.config import settings
from app.models.settlement import Settlement
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


@dataclass
class RuleResult:
    """Result of financial rule evaluation."""
    passed: bool
    rule_name: str
    explanation: str
    confidence_adjustment: float = 0.0


@dataclass
class RuleEvaluation:
    """All rule evaluation results for a transaction."""
    results: List[RuleResult] = field(default_factory=list)
    overall_passed: bool = True
    is_fee_explainable: bool = False
    is_partial_payment: bool = False
    is_duplicate_flagged: bool = False
    is_settlement_delayed: bool = False
    confidence_bonus: float = 0.0

    @property
    def explanations(self) -> List[str]:
        return [r.explanation for r in self.results if r.explanation]


def evaluate_rules(
    txn: Transaction,
    expected_amount: Optional[Decimal] = None,
    actual_amount: Optional[Decimal] = None,
    settlement: Optional[Settlement] = None,
    date_difference_days: Optional[int] = None,
) -> RuleEvaluation:
    """
    Evaluate all financial rules for a transaction.

    Returns a RuleEvaluation with findings.
    """
    evaluation = RuleEvaluation()

    # Rule 1: Fee tolerance
    if settlement and txn.amount:
        fee_result = _check_fee_tolerance(txn.amount, settlement)
        evaluation.results.append(fee_result)
        if fee_result.passed:
            evaluation.is_fee_explainable = True
            evaluation.confidence_bonus += fee_result.confidence_adjustment

    # Rule 2: Amount mismatch — check if explainable
    if expected_amount and actual_amount:
        diff = abs(expected_amount - actual_amount)
        if diff > 0:
            partial_result = _check_partial_payment(expected_amount, actual_amount)
            evaluation.results.append(partial_result)
            if partial_result.passed:
                evaluation.is_partial_payment = True

    # Rule 3: Settlement delay
    if date_difference_days is not None:
        delay_result = _check_settlement_delay(date_difference_days)
        evaluation.results.append(delay_result)
        if not delay_result.passed:
            evaluation.is_settlement_delayed = True

    # Overall pass/fail
    hard_failures = [r for r in evaluation.results if not r.passed and r.confidence_adjustment < -0.1]
    evaluation.overall_passed = len(hard_failures) == 0

    return evaluation


def _check_fee_tolerance(gross_amount: Decimal, settlement: Settlement) -> RuleResult:
    """Check if the settlement fee is within the configured tolerance."""
    if gross_amount == 0:
        return RuleResult(passed=True, rule_name="fee_tolerance", explanation="Zero amount — no fee check.")

    total_fees = settlement.fees + settlement.tax
    fee_rate = total_fees / gross_amount

    max_fee_rate = Decimal(str(settings.fee_tolerance_percent))

    if fee_rate <= max_fee_rate:
        return RuleResult(
            passed=True,
            rule_name="fee_tolerance",
            explanation=f"Settlement fee ({float(fee_rate)*100:.2f}%) within tolerance ({float(max_fee_rate)*100:.1f}%).",
            confidence_adjustment=0.05,
        )
    else:
        return RuleResult(
            passed=False,
            rule_name="fee_tolerance",
            explanation=f"Settlement fee ({float(fee_rate)*100:.2f}%) exceeds tolerance ({float(max_fee_rate)*100:.1f}%).",
            confidence_adjustment=-0.10,
        )


def _check_partial_payment(expected: Decimal, actual: Decimal) -> RuleResult:
    """Check if actual amount looks like a partial payment."""
    if expected == 0:
        return RuleResult(passed=False, rule_name="partial_payment", explanation="Zero expected amount.")

    ratio = actual / expected
    tolerance = Decimal(str(1 - settings.partial_payment_tolerance_percent))

    if tolerance <= ratio <= Decimal("1"):
        return RuleResult(
            passed=True,
            rule_name="partial_payment",
            explanation=f"Amount ({float(ratio)*100:.1f}% of expected) is within partial payment tolerance.",
        )
    return RuleResult(
        passed=False,
        rule_name="partial_payment",
        explanation=f"Amount shortfall ({float(1-ratio)*100:.1f}%) exceeds partial payment tolerance.",
    )


def _check_settlement_delay(date_diff_days: int) -> RuleResult:
    """Check if settlement delay is within tolerance."""
    threshold = settings.settlement_delay_days
    if date_diff_days <= threshold:
        return RuleResult(
            passed=True,
            rule_name="settlement_delay",
            explanation=f"Settlement arrived within {date_diff_days} day(s) — within {threshold}-day threshold.",
        )
    return RuleResult(
        passed=False,
        rule_name="settlement_delay",
        explanation=f"Settlement delayed by {date_diff_days} day(s) — exceeds {threshold}-day threshold.",
        confidence_adjustment=-0.05,
    )
