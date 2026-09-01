"""Finova — Tests: Confidence Scoring."""
import pytest
from decimal import Decimal
from datetime import datetime

from app.services.finance_engine.confidence import compute_confidence
from app.models.transaction import Transaction, PaymentStatus, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank_transaction import BankTransaction


def _txn(**kw):
    return Transaction(
        transaction_id=kw.get("transaction_id", "TXN-001"),
        customer_id=kw.get("customer_id", "CUST-001"),
        amount=kw.get("amount", Decimal("10000")),
        timestamp=kw.get("timestamp", datetime(2024, 1, 15)),
        reference_id=kw.get("reference_id", "REF-001"),
        invoice_id=kw.get("invoice_id", "INV-001"),
        payment_status=PaymentStatus.CAPTURED,
        payment_method=PaymentMethod.UPI,
    )


def test_high_confidence_all_signals():
    txn = _txn()
    inv = Invoice(
        invoice_id="INV-001", customer_id="CUST-001",
        invoice_amount=Decimal("10000"), tax=Decimal("0"), total_amount=Decimal("10000"),
        date=datetime(2024, 1, 15), status=InvoiceStatus.PAID,
    )
    bank = BankTransaction(
        bank_transaction_id="BNK-001", date=datetime(2024, 1, 15),
        amount=Decimal("9800"), reference="REF-001",
    )
    result = compute_confidence(txn, inv, bank, date_difference_days=0)
    assert result.confidence >= 0.75
    assert result.signals.reference_match
    assert result.signals.customer_match
    assert result.signals.invoice_match


def test_low_confidence_no_signals():
    txn = _txn(reference_id=None, invoice_id=None, customer_id="CUST-999")
    result = compute_confidence(txn)
    assert result.confidence < 0.50


def test_confidence_between_zero_and_one():
    """Confidence is always in [0, 1]."""
    txn = _txn()
    result = compute_confidence(txn, amount_difference=Decimal("5000"), date_difference_days=60)
    assert 0.0 <= result.confidence <= 1.0


def test_confidence_signals_breakdown():
    txn = _txn()
    inv = Invoice(
        invoice_id="INV-001", customer_id="CUST-001",
        invoice_amount=Decimal("10000"), tax=Decimal("0"), total_amount=Decimal("10000"),
        date=datetime(2024, 1, 15), status=InvoiceStatus.UNPAID,
    )
    result = compute_confidence(txn, inv, date_difference_days=1)
    # Score breakdown must have expected keys
    assert "reference" in result.score_breakdown
    assert "amount" in result.score_breakdown
    assert "customer" in result.score_breakdown
    assert "date" in result.score_breakdown


def test_medium_confidence_range():
    """Medium confidence for partial match."""
    txn = _txn(reference_id="REF-001")
    inv = Invoice(
        invoice_id="INV-001", customer_id="CUST-001",
        invoice_amount=Decimal("10000"), tax=Decimal("0"), total_amount=Decimal("10000"),
        date=datetime(2024, 1, 20), status=InvoiceStatus.UNPAID,  # 5 day diff
    )
    bank = BankTransaction(
        bank_transaction_id="BNK-001", date=datetime(2024, 1, 16),
        amount=Decimal("9500"), reference="REF-001",
    )
    result = compute_confidence(txn, inv, bank, date_difference_days=5)
    assert 0.50 <= result.confidence <= 0.95
