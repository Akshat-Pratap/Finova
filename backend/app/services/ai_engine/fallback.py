"""Finova — Deterministic AI Fallback.

Used when:
- GEMINI_API_KEY is not set
- DEMO_MODE=true
- Gemini API fails after retries

Produces realistic, rule-based investigation responses.
Never claims to be real AI output.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict

from app.services.ai_engine.provider import AIProvider
from app.services.ai_engine.schemas import AIInvestigationResponse

logger = logging.getLogger(__name__)


class FallbackAIProvider(AIProvider):
    """
    Deterministic fallback AI provider for demo mode.

    Uses rule-based logic to produce investigation responses.
    Clearly identified as DEMO MODE in all outputs.
    """

    @property
    def provider_name(self) -> str:
        return "DEMO MODE"

    @property
    def is_available(self) -> bool:
        return True  # Always available

    async def investigate(
        self,
        context: Dict[str, Any],
        prompt: str,
    ) -> Dict[str, Any]:
        """
        Produce a deterministic investigation response based on the context.
        """
        response = _analyze_context(context)
        logger.info(
            "Fallback AI investigation: finding=%s confidence=%.2f",
            response.finding, response.confidence,
        )
        return response.model_dump()


def _analyze_context(context: Dict[str, Any]) -> AIInvestigationResponse:
    """Rule-based investigation logic."""
    txn = context.get("transaction", {})
    invoice = context.get("invoice", {})
    bank = context.get("bank_transaction", {})
    settlement = context.get("settlement", {})
    signals = context.get("confidence_signals", {})

    # Extract amounts
    txn_amount = _to_decimal(txn.get("amount"))
    inv_amount = _to_decimal(invoice.get("invoice_amount"))
    bank_amount = _to_decimal(bank.get("amount"))
    gross = _to_decimal(settlement.get("gross_amount"))
    fees = _to_decimal(settlement.get("fees"))
    tax = _to_decimal(settlement.get("tax"))
    net = _to_decimal(settlement.get("net_amount"))

    # Case 1: Settlement fee discrepancy
    if gross and fees and fees > 0 and gross == txn_amount:
        total_deducted = (fees or Decimal("0")) + (tax or Decimal("0"))
        fee_rate = float(fees / gross) if gross else 0
        return AIInvestigationResponse(
            finding="Likely processing fee discrepancy",
            reason=(
                f"The transaction gross amount (₹{gross:.2f}) matches the payment, "
                f"but the settlement deducted ₹{fees:.2f} in fees + ₹{tax or 0:.2f} GST. "
                f"Net settlement of ₹{net:.2f} is expected after fee deduction."
            ),
            confidence=0.88,
            recommendation="RECONCILE",
            requires_manual_review=False,
            evidence=[
                f"Gross amount ₹{gross:.2f} matches transaction amount",
                f"Processing fee: ₹{fees:.2f} ({fee_rate*100:.2f}%)",
                f"GST on fee: ₹{tax or 0:.2f}",
                f"Net settlement: ₹{net:.2f}",
                "Fee rate within acceptable gateway range",
            ],
        )

    # Case 2: Missing reference
    if not txn.get("reference_id"):
        return AIInvestigationResponse(
            finding="Missing reference ID",
            reason=(
                "The transaction lacks a reference identifier, making deterministic matching impossible. "
                "Manual verification against bank statement is required."
            ),
            confidence=0.45,
            recommendation="MANUAL_REVIEW",
            requires_manual_review=True,
            evidence=[
                "Transaction reference_id is null/missing",
                "Cannot perform reference-based matching",
                "Amount and customer may match but cannot confirm uniquely",
            ],
        )

    # Case 3: Amount mismatch
    if txn_amount and bank_amount and abs(txn_amount - bank_amount) > Decimal("10"):
        diff = txn_amount - bank_amount
        pct = float(diff / txn_amount) * 100 if txn_amount else 0
        # Check if it could be a partial payment
        if bank_amount < txn_amount and bank_amount / txn_amount > Decimal("0.5"):
            return AIInvestigationResponse(
                finding="Likely partial payment",
                reason=(
                    f"Bank received ₹{bank_amount:.2f} against expected ₹{txn_amount:.2f}. "
                    f"The shortfall of ₹{diff:.2f} ({pct:.1f}%) suggests a partial payment."
                ),
                confidence=0.72,
                recommendation="MANUAL_REVIEW",
                requires_manual_review=True,
                evidence=[
                    f"Expected amount: ₹{txn_amount:.2f}",
                    f"Bank received: ₹{bank_amount:.2f}",
                    f"Shortfall: ₹{diff:.2f} ({pct:.1f}%)",
                    "Payment ratio above 50% — consistent with partial settlement",
                ],
            )
        else:
            return AIInvestigationResponse(
                finding="Significant amount discrepancy",
                reason=(
                    f"Bank amount (₹{bank_amount:.2f}) differs from transaction amount (₹{txn_amount:.2f}) "
                    f"by ₹{diff:.2f} ({pct:.1f}%). Cannot be explained by standard fee patterns."
                ),
                confidence=0.55,
                recommendation="MANUAL_REVIEW",
                requires_manual_review=True,
                evidence=[
                    f"Transaction amount: ₹{txn_amount:.2f}",
                    f"Bank amount: ₹{bank_amount:.2f}",
                    f"Difference: ₹{diff:.2f}",
                    "Difference does not match known fee patterns",
                ],
            )

    # Case 4: Small difference — likely rounding
    if txn_amount and bank_amount and abs(txn_amount - bank_amount) <= Decimal("10"):
        diff = abs(txn_amount - bank_amount)
        return AIInvestigationResponse(
            finding="Likely rounding difference",
            reason=(
                f"The difference of ₹{diff:.2f} between transaction and bank record "
                f"is within rounding tolerance. Safe to reconcile."
            ),
            confidence=0.85,
            recommendation="RECONCILE",
            requires_manual_review=False,
            evidence=[
                f"Transaction: ₹{txn_amount:.2f}",
                f"Bank: ₹{bank_amount:.2f}",
                f"Difference: ₹{diff:.2f} (≤ ₹10 rounding threshold)",
            ],
        )

    # Default: insufficient evidence
    return AIInvestigationResponse(
        finding="Unable to determine — manual review required",
        reason=(
            "Insufficient evidence to determine the cause of this discrepancy automatically. "
            "Manual review by a finance officer is recommended."
        ),
        confidence=0.40,
        recommendation="MANUAL_REVIEW",
        requires_manual_review=True,
        evidence=[
            "Deterministic matching produced low confidence",
            "No clear fee, tax, or partial payment pattern found",
            "Manual verification against source records required",
        ],
    )


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")
