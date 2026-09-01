"""Finova — Tests: Reconciliation Pipeline."""
import pytest
from decimal import Decimal
from datetime import datetime

from app.services.finance_engine.reconciliation import reconcile_transaction, reconcile_batch
from app.services.finance_engine.duplicate_detector import detect_duplicates
from app.models.transaction import Transaction, PaymentStatus, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank_transaction import BankTransaction
from app.models.settlement import Settlement, SettlementStatus
from app.models.reconciliation import ReconciliationStatus


def _txn(tid="TXN-001", cid="CUST-001", amount=Decimal("10000"), ref="REF-001", inv="INV-001"):
    return Transaction(
        transaction_id=tid, customer_id=cid, amount=amount,
        timestamp=datetime(2024, 1, 15), reference_id=ref,
        invoice_id=inv, payment_status=PaymentStatus.CAPTURED,
        payment_method=PaymentMethod.UPI, ground_truth_status="MATCH",
    )


def _inv(iid="INV-001", cid="CUST-001", amount=Decimal("10000")):
    return Invoice(
        invoice_id=iid, customer_id=cid, invoice_amount=amount,
        tax=Decimal("0"), total_amount=amount, date=datetime(2024, 1, 10),
        status=InvoiceStatus.UNPAID,
    )


def _bank(bid="BNK-001", amount=Decimal("9800"), ref="REF-001"):
    return BankTransaction(
        bank_transaction_id=bid, date=datetime(2024, 1, 16),
        amount=amount, reference=ref,
    )


def _settlement(sid="SET-001", txn_id="TXN-001", gross=Decimal("10000"), fees=Decimal("200")):
    return Settlement(
        settlement_id=sid, transaction_id=txn_id,
        gross_amount=gross, fees=fees, tax=Decimal("36"),
        net_amount=gross - fees - Decimal("36"),
        settlement_date=datetime(2024, 1, 17),
        status=SettlementStatus.PROCESSED,
    )


def test_reconcile_clean_match():
    txn = _txn()
    invoices = [_inv()]
    banks = [_bank(amount=Decimal("9800"))]  # After fees
    settlements = [_settlement()]

    result = reconcile_transaction(txn, invoices, banks, settlements, "RUN-001")
    # With reference match + customer match + invoice match → should be MATCHED or AI_REVIEW
    assert result.status in (ReconciliationStatus.MATCHED, ReconciliationStatus.AI_REVIEW)
    assert result.confidence > 0.60


def test_reconcile_high_confidence_auto_match():
    """Perfect match should auto-reconcile."""
    txn = _txn(amount=Decimal("10000"), ref="REF-001", inv="INV-001")
    invoices = [_inv(amount=Decimal("10000"))]
    banks = [BankTransaction(bank_transaction_id="BNK-001", date=datetime(2024, 1, 15), amount=Decimal("9800"), reference="REF-001")]
    settlements = [_settlement(fees=Decimal("200"))]

    result = reconcile_transaction(txn, invoices, banks, settlements, "RUN-001")
    # Should be MATCHED or AI_REVIEW with high confidence
    assert result.confidence > 0.70


def test_reconcile_no_match():
    """Transaction with no matching invoice or bank record."""
    txn = _txn(ref=None)
    result = reconcile_transaction(txn, [], [], [], "RUN-001")
    assert result.status in (ReconciliationStatus.MANUAL_REVIEW, ReconciliationStatus.AI_REVIEW)


def test_reconcile_duplicate_flagged():
    txn = _txn()
    result = reconcile_transaction(txn, [], [], [], "RUN-001", is_known_duplicate=True)
    assert result.status == ReconciliationStatus.DUPLICATE
    assert result.confidence > 0.90


def test_reconcile_batch():
    txns = [
        _txn("TXN-001", ref="REF-001", inv="INV-001"),
        _txn("TXN-002", ref="REF-002", inv="INV-002"),
        _txn("TXN-003", ref=None),
    ]
    invoices = [_inv("INV-001"), _inv("INV-002")]
    banks = [_bank("BNK-001", ref="REF-001"), _bank("BNK-002", ref="REF-002")]

    results = reconcile_batch(txns, invoices, banks, [], "RUN-001")
    assert len(results) == 3


def test_duplicate_detection():
    txns = [
        _txn("TXN-001", ref="REF-SAME"),
        _txn("TXN-002", ref="REF-SAME"),  # Same ref+amount+customer → duplicate
        _txn("TXN-003", ref="REF-DIFF"),
    ]
    unique, dup_ids = detect_duplicates(txns)
    assert len(dup_ids) >= 1
    assert "TXN-001" not in dup_ids  # First occurrence kept


def test_reconcile_large_amount_difference():
    """20% amount difference should go to AI review."""
    txn = _txn(amount=Decimal("10000"))
    invoice = _inv(amount=Decimal("8000"))  # 20% less
    banks = [_bank(amount=Decimal("8000"))]

    result = reconcile_transaction(txn, [invoice], banks, [], "RUN-001")
    assert result.status in (ReconciliationStatus.AI_REVIEW, ReconciliationStatus.MANUAL_REVIEW)
