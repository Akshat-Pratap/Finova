"""Finova — AI Investigation Prompts.

Structured prompts for financial investigation.
Never ask the AI to invent or modify source financial data.
"""
from __future__ import annotations

from typing import Any, Dict


SYSTEM_PROMPT = """You are Finova's AI Financial Investigator.

Your role is to investigate financial discrepancies between payment transactions, invoices, bank statements, and settlements.

STRICT RULES:
1. Never invent transactions, invoices, or financial values.
2. Never modify or contradict source financial records.
3. Only make claims supported by the evidence provided.
4. When evidence is insufficient, set requires_manual_review = true.
5. Return only valid JSON matching the required schema.
6. Be concise and factual. Do not speculate without evidence.

RESPONSE FORMAT (return exactly this JSON):
{
  "finding": "<brief finding label>",
  "reason": "<evidence-based explanation, 1-3 sentences>",
  "confidence": <float 0.0-1.0>,
  "recommendation": "<RECONCILE | MANUAL_REVIEW | REJECT>",
  "requires_manual_review": <true | false>,
  "evidence": ["<evidence point 1>", "<evidence point 2>", ...]
}

Possible findings:
- "Likely processing fee discrepancy"
- "Likely GST/tax deduction"
- "Likely partial payment"
- "Likely duplicate transaction"
- "Likely settlement delay"
- "Likely rounding difference"
- "Customer mapping discrepancy"
- "Unable to determine — manual review required"
"""


def build_investigation_prompt(context: Dict[str, Any]) -> str:
    """Build a structured investigation prompt from transaction context."""
    txn = context.get("transaction", {})
    invoice = context.get("invoice", {})
    bank = context.get("bank_transaction", {})
    settlement = context.get("settlement", {})
    signals = context.get("confidence_signals", {})
    rules = context.get("rule_results", [])
    confidence = context.get("confidence_score", 0)

    prompt = f"""FINANCIAL DISCREPANCY INVESTIGATION

== TRANSACTION ==
Transaction ID: {txn.get('transaction_id', 'N/A')}
Customer ID: {txn.get('customer_id', 'N/A')}
Amount: ₹{txn.get('amount', 'N/A')}
Reference: {txn.get('reference_id', 'MISSING')}
Invoice ID: {txn.get('invoice_id', 'N/A')}
Date: {txn.get('timestamp', 'N/A')}
Payment Method: {txn.get('payment_method', 'N/A')}
Status: {txn.get('payment_status', 'N/A')}

== INVOICE ==
{_format_section(invoice, ['invoice_id', 'customer_id', 'invoice_amount', 'total_amount', 'date', 'status'])}

== BANK RECORD ==
{_format_section(bank, ['bank_transaction_id', 'date', 'amount', 'reference', 'description'])}

== SETTLEMENT ==
{_format_section(settlement, ['settlement_id', 'gross_amount', 'fees', 'tax', 'net_amount', 'settlement_date', 'status'])}

== MATCHING SIGNALS ==
Reference match: {signals.get('reference_match', False)}
Amount match: {signals.get('amount_match', False)}
Customer match: {signals.get('customer_match', False)}
Amount difference: ₹{signals.get('amount_difference', 'N/A')}
Date difference: {signals.get('date_difference_days', 'N/A')} days
Deterministic confidence: {confidence:.0%}

== RULE EVALUATION ==
{_format_rules(rules)}

Based on the above evidence, investigate this discrepancy and return a JSON response.
"""
    return prompt


def _format_section(data: Dict, fields: list) -> str:
    if not data:
        return "(no data available)"
    lines = []
    for field in fields:
        val = data.get(field, "N/A")
        if val is not None:
            lines.append(f"{field}: {val}")
    return "\n".join(lines) or "(no data available)"


def _format_rules(rules: list) -> str:
    if not rules:
        return "(no rules evaluated)"
    return "\n".join(f"- {r}" for r in rules)
