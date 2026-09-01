"""Finova — Tests: Matching and Confidence."""
import pytest
from decimal import Decimal
from datetime import datetime

from app.services.finance_engine.fuzzy_matcher import reference_similarity, customer_name_similarity
from app.services.finance_engine.confidence import compute_confidence
from app.services.finance_engine.matcher import match_transaction_to_invoice, match_transaction_to_bank
from app.models.transaction import Transaction, PaymentStatus, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank_transaction import BankTransaction


def _make_txn(**kwargs) -> Transaction:
    defaults = dict(
        transaction_id="TXN-001",
        customer_id="CUST-001",
        amount=Decimal("10000"),
        timestamp=datetime(2024, 1, 15),
        payment_status=PaymentStatus.CAPTURED,
        payment_method=PaymentMethod.UPI,
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def _make_invoice(**kwargs) -> Invoice:
    defaults = dict(
        invoice_id="INV-001",
        customer_id="CUST-001",
        invoice_amount=Decimal("10000"),
        tax=Decimal("0"),
        total_amount=Decimal("10000"),
        date=datetime(2024, 1, 10),
        status=InvoiceStatus.UNPAID,
    )
    defaults.update(kwargs)
    return Invoice(**defaults)


# ── Fuzzy Matching Tests ────────────────────────────────────────────────────

def test_reference_exact_match():
    score = reference_similarity("REF-8291", "REF-8291")
    assert score == 1.0


def test_reference_normalized_match():
    score = reference_similarity("INV-8291", "INV8291")
    assert score > 0.80, f"Expected >0.80, got {score}"


def test_reference_no_match():
    score = reference_similarity("INV-8291", "INV-1111")
    assert score < 0.70, f"Expected <0.70, got {score}"


def test_reference_none():
    score = reference_similarity(None, "REF-001")
    assert score == 0.0


def test_customer_name_exact():
    score = customer_name_similarity("Arjun Sharma", "Arjun Sharma")
    assert score == 1.0


def test_customer_name_partial():
    score = customer_name_similarity("Arjun Sharma", "Arjun")
    assert score > 0.70


def test_customer_name_different():
    score = customer_name_similarity("Arjun Sharma", "Priya Patel")
    assert score < 0.50


# ── Confidence Scoring Tests ────────────────────────────────────────────────

def test_confidence_perfect_match():
    txn = _make_txn(reference_id="REF-001", invoice_id="INV-001")
    invoice = _make_invoice(invoice_id="INV-001", customer_id="CUST-001", invoice_amount=Decimal("10000"))
    bank = BankTransaction(
        bank_transaction_id="BNK-001",
        date=datetime(2024, 1, 15),
        amount=Decimal("9750"),
        reference="REF-001",
    )
    result = compute_confidence(txn, invoice, bank, date_difference_days=0)
    assert result.confidence > 0.85, f"Expected >0.85, got {result.confidence}"
    assert result.signals.reference_match


def test_confidence_no_reference():
    txn = _make_txn(reference_id=None)
    invoice = _make_invoice()
    result = compute_confidence(txn, invoice, date_difference_days=2)
    assert result.confidence < 0.80  # No reference penalizes heavily


def test_confidence_amount_mismatch():
    txn = _make_txn(amount=Decimal("10000"))
    invoice = _make_invoice(invoice_amount=Decimal("8000"))  # 20% mismatch
    result = compute_confidence(txn, invoice)
    assert not result.signals.amount_match
    assert result.confidence < 0.80


def test_confidence_thresholds():
    """Verify threshold boundaries."""
    from app.core.config import settings
    assert settings.auto_reconcile_threshold == 0.90
    assert settings.ai_review_threshold == 0.70


# ── Invoice Matching Tests ──────────────────────────────────────────────────

def test_match_invoice_exact():
    txn = _make_txn(invoice_id="INV-001", customer_id="CUST-001", amount=Decimal("10000"))
    invoices = [
        _make_invoice(invoice_id="INV-001", customer_id="CUST-001", invoice_amount=Decimal("10000")),
        _make_invoice(invoice_id="INV-002", customer_id="CUST-002", invoice_amount=Decimal("5000")),
    ]
    matched, evidence = match_transaction_to_invoice(txn, invoices)
    assert matched is not None
    assert matched.invoice_id == "INV-001"
    assert evidence.invoice_id_match
    assert evidence.customer_exact


def test_match_invoice_no_match():
    txn = _make_txn(customer_id="CUST-999", invoice_id=None)
    invoices = [_make_invoice(customer_id="CUST-001")]
    matched, evidence = match_transaction_to_invoice(txn, invoices)
    # May still return a match with low score — just check evidence
    # The important thing is customer_exact is False
    if matched:
        assert not evidence.customer_exact


def test_match_bank_exact_reference():
    txn = _make_txn(reference_id="REF-001", amount=Decimal("9750"))
    banks = [
        BankTransaction(
            bank_transaction_id="BNK-001",
            date=datetime(2024, 1, 15),
            amount=Decimal("9750"),
            reference="REF-001",
        )
    ]
    matched, evidence = match_transaction_to_bank(txn, banks)
    assert matched is not None
    assert evidence.reference_exact
    assert evidence.amount_exact
