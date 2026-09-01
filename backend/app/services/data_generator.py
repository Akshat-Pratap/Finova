"""Finova — Synthetic Financial Dataset Generator.

Generates realistic financial datasets with controlled anomalies for testing
and benchmarking. Includes ground-truth labels for precision/recall metrics.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app.models.transaction import Transaction, PaymentMethod, PaymentStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank_transaction import BankTransaction
from app.models.settlement import Settlement, SettlementStatus


# ---------------------------------------------------------------------------
# Realistic name / reference pools
# ---------------------------------------------------------------------------
CUSTOMER_NAMES = [
    "Arjun Sharma", "Priya Patel", "Rahul Gupta", "Sunita Reddy", "Vikram Mehta",
    "Ananya Iyer", "Deepak Kumar", "Meera Nair", "Sanjay Joshi", "Kavitha Pillai",
    "Rohan Singh", "Neha Verma", "Amit Desai", "Pooja Rao", "Kiran Malhotra",
    "Suresh Nair", "Divya Krishnan", "Mohit Agarwal", "Sneha Bhatt", "Arun Menon",
    "Ramesh Tiwari", "Lakshmi Subramaniam", "Gaurav Bose", "Priti Sinha", "Vinay Kulkarni",
]

PAYMENT_METHODS = [
    PaymentMethod.UPI, PaymentMethod.CARD, PaymentMethod.NETBANKING,
    PaymentMethod.WALLET, PaymentMethod.EMI,
]

COMMON_FEE_RATES = [Decimal("0.02"), Decimal("0.025"), Decimal("0.018"), Decimal("0.03")]
GST_RATE = Decimal("0.18")


def _random_amount(min_val: int = 500, max_val: int = 100000) -> Decimal:
    """Generate a realistic INR amount."""
    # Prefer round numbers
    base = random.randint(min_val // 100, max_val // 100) * 100
    # Sometimes add cents-like variation
    if random.random() < 0.2:
        base += random.choice([50, 99, 149, 199, 249, 499])
    return Decimal(str(base))


def _random_date(days_back: int = 90) -> datetime:
    """Random date within the last N days."""
    offset = random.randint(0, days_back)
    return datetime.utcnow() - timedelta(days=offset, hours=random.randint(0, 23))


def _customer_id(name: str, idx: int) -> str:
    """Stable customer ID from name."""
    return f"CUST-{abs(hash(name)) % 10000:04d}"


def generate_dataset(
    num_records: int = 250,
    seed: int = 42,
    anomaly_rates: Optional[Dict[str, float]] = None,
) -> Tuple[List[Transaction], List[Invoice], List[BankTransaction], List[Settlement]]:
    """
    Generate a synthetic financial dataset.

    Returns (transactions, invoices, bank_transactions, settlements).

    Anomaly distribution (default):
        70% clean matches
        10% amount mismatches
         5% duplicates
         5% missing references
         5% partial payments
         5% fee/settlement anomalies
    """
    random.seed(seed)

    if anomaly_rates is None:
        anomaly_rates = {
            "clean": 0.70,
            "amount_mismatch": 0.10,
            "duplicate": 0.05,
            "missing_reference": 0.05,
            "partial_payment": 0.05,
            "fee_anomaly": 0.05,
        }

    transactions: List[Transaction] = []
    invoices: List[Invoice] = []
    bank_transactions: List[BankTransaction] = []
    settlements: List[Settlement] = []

    # Pre-assign anomaly types to record indices
    categories = _distribute_anomalies(num_records, anomaly_rates)

    for i, category in enumerate(categories):
        txn, inv, bank_txn, settlement = _generate_record(i, category)
        transactions.append(txn)
        invoices.append(inv)
        if bank_txn:
            bank_transactions.append(bank_txn)
        if settlement:
            settlements.append(settlement)

    # Add a few extra duplicate bank transactions for realism
    return transactions, invoices, bank_transactions, settlements


def _distribute_anomalies(n: int, rates: Dict[str, float]) -> List[str]:
    """Assign anomaly category to each record index."""
    categories = []
    for category, rate in rates.items():
        count = round(n * rate)
        categories.extend([category] * count)
    # Fill remainder with clean
    while len(categories) < n:
        categories.append("clean")
    categories = categories[:n]
    random.shuffle(categories)
    return categories


def _generate_record(
    idx: int,
    category: str,
) -> Tuple[Transaction, Invoice, Optional[BankTransaction], Optional[Settlement]]:
    """Generate a single complete record set for the given anomaly category."""
    customer_name = random.choice(CUSTOMER_NAMES)
    customer_id = _customer_id(customer_name, idx)
    txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    inv_id = f"INV-{random.randint(1000, 9999)}"
    ref_id = f"REF-{uuid.uuid4().hex[:6].upper()}"
    amount = _random_amount()
    txn_date = _random_date(60)
    fee_rate = random.choice(COMMON_FEE_RATES)
    fee = (amount * fee_rate).quantize(Decimal("0.01"))
    tax_on_fee = (fee * GST_RATE).quantize(Decimal("0.01"))
    net = amount - fee - tax_on_fee

    # Invoice
    tax = (amount * Decimal("0.18")).quantize(Decimal("0.01"))
    invoice = Invoice(
        invoice_id=inv_id,
        customer_id=customer_id,
        invoice_amount=amount,
        tax=tax,
        total_amount=amount + tax,
        date=txn_date - timedelta(days=random.randint(1, 30)),
        due_date=txn_date + timedelta(days=30),
        status=InvoiceStatus.UNPAID,
    )

    if category == "clean":
        return _clean_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date)

    elif category == "amount_mismatch":
        return _amount_mismatch_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, txn_date)

    elif category == "duplicate":
        return _duplicate_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date)

    elif category == "missing_reference":
        return _missing_reference_record(txn_id, inv_id, customer_id, amount, fee, tax_on_fee, net, txn_date)

    elif category == "partial_payment":
        return _partial_payment_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date)

    elif category == "fee_anomaly":
        return _fee_anomaly_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date)

    else:
        return _clean_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date)


# ---------------------------------------------------------------------------
# Individual anomaly generators
# ---------------------------------------------------------------------------

def _clean_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date):
    """Perfectly matching record."""
    txn = Transaction(
        transaction_id=txn_id,
        order_id=f"ORD-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer_id,
        amount=amount,
        payment_status=PaymentStatus.CAPTURED,
        payment_method=random.choice(PAYMENT_METHODS),
        timestamp=txn_date,
        reference_id=ref_id,
        invoice_id=inv_id,
        ground_truth_status="MATCH",
    )
    invoice = Invoice(
        invoice_id=inv_id,
        customer_id=customer_id,
        invoice_amount=amount,
        tax=Decimal("0"),
        total_amount=amount,
        date=txn_date - timedelta(days=random.randint(1, 15)),
        status=InvoiceStatus.PAID,
    )
    bank_txn = BankTransaction(
        bank_transaction_id=f"BNK-{uuid.uuid4().hex[:8].upper()}",
        date=txn_date + timedelta(days=random.randint(0, 2)),
        amount=net,
        description=f"Payment {ref_id}",
        reference=ref_id,
        account="ACC-001",
    )
    settlement = Settlement(
        settlement_id=f"SET-{uuid.uuid4().hex[:8].upper()}",
        transaction_id=txn_id,
        gross_amount=amount,
        fees=fee,
        tax=tax_on_fee,
        net_amount=net,
        settlement_date=txn_date + timedelta(days=random.randint(1, 3)),
        status=SettlementStatus.PROCESSED,
    )
    return txn, invoice, bank_txn, settlement


def _amount_mismatch_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, txn_date):
    """Bank received a different amount than expected."""
    wrong_factor = random.choice([Decimal("0.85"), Decimal("0.90"), Decimal("1.10"), Decimal("1.15")])
    bank_amount = (amount * wrong_factor).quantize(Decimal("0.01"))
    txn = Transaction(
        transaction_id=txn_id,
        customer_id=customer_id,
        amount=amount,
        payment_status=PaymentStatus.CAPTURED,
        payment_method=random.choice(PAYMENT_METHODS),
        timestamp=txn_date,
        reference_id=ref_id,
        invoice_id=inv_id,
        ground_truth_status="MISMATCH",
    )
    invoice = Invoice(
        invoice_id=inv_id,
        customer_id=customer_id,
        invoice_amount=amount,
        tax=Decimal("0"),
        total_amount=amount,
        date=txn_date - timedelta(days=5),
        status=InvoiceStatus.PARTIAL,
    )
    bank_txn = BankTransaction(
        bank_transaction_id=f"BNK-{uuid.uuid4().hex[:8].upper()}",
        date=txn_date + timedelta(days=1),
        amount=bank_amount,
        description=f"Payment {ref_id}",
        reference=ref_id,
        account="ACC-001",
    )
    return txn, invoice, bank_txn, None


def _duplicate_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date):
    """Transaction is a near-duplicate of another."""
    # Create a second transaction with same ref and amount
    dup_txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    txn = Transaction(
        transaction_id=dup_txn_id,
        customer_id=customer_id,
        amount=amount,
        payment_status=PaymentStatus.CAPTURED,
        payment_method=random.choice(PAYMENT_METHODS),
        timestamp=txn_date + timedelta(minutes=random.randint(1, 30)),
        reference_id=ref_id,  # Same reference — duplicate signal
        invoice_id=inv_id,
        ground_truth_status="DUPLICATE",
    )
    invoice = Invoice(
        invoice_id=inv_id,
        customer_id=customer_id,
        invoice_amount=amount,
        tax=Decimal("0"),
        total_amount=amount,
        date=txn_date - timedelta(days=2),
        status=InvoiceStatus.PAID,
    )
    bank_txn = BankTransaction(
        bank_transaction_id=f"BNK-{uuid.uuid4().hex[:8].upper()}",
        date=txn_date + timedelta(hours=2),
        amount=net,
        description=f"Payment {ref_id} DUPLICATE",
        reference=ref_id,
        account="ACC-001",
    )
    return txn, invoice, bank_txn, None


def _missing_reference_record(txn_id, inv_id, customer_id, amount, fee, tax_on_fee, net, txn_date):
    """Transaction has no reference ID — hard to match."""
    txn = Transaction(
        transaction_id=txn_id,
        customer_id=customer_id,
        amount=amount,
        payment_status=PaymentStatus.CAPTURED,
        payment_method=random.choice(PAYMENT_METHODS),
        timestamp=txn_date,
        reference_id=None,  # Missing!
        invoice_id=inv_id,
        ground_truth_status="EXCEPTION",
    )
    invoice = Invoice(
        invoice_id=inv_id,
        customer_id=customer_id,
        invoice_amount=amount,
        tax=Decimal("0"),
        total_amount=amount,
        date=txn_date - timedelta(days=7),
        status=InvoiceStatus.UNPAID,
    )
    bank_txn = BankTransaction(
        bank_transaction_id=f"BNK-{uuid.uuid4().hex[:8].upper()}",
        date=txn_date + timedelta(days=1),
        amount=net,
        description="Payment received",  # No reference
        reference=None,
        account="ACC-001",
    )
    return txn, invoice, bank_txn, None


def _partial_payment_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date):
    """Customer paid only part of the invoice."""
    partial_ratio = random.choice([Decimal("0.5"), Decimal("0.6"), Decimal("0.75"), Decimal("0.8")])
    partial_amount = (amount * partial_ratio).quantize(Decimal("0.01"))
    txn = Transaction(
        transaction_id=txn_id,
        customer_id=customer_id,
        amount=partial_amount,
        payment_status=PaymentStatus.CAPTURED,
        payment_method=random.choice(PAYMENT_METHODS),
        timestamp=txn_date,
        reference_id=ref_id,
        invoice_id=inv_id,
        ground_truth_status="MISMATCH",
    )
    invoice = Invoice(
        invoice_id=inv_id,
        customer_id=customer_id,
        invoice_amount=amount,  # Full amount expected
        tax=Decimal("0"),
        total_amount=amount,
        date=txn_date - timedelta(days=10),
        status=InvoiceStatus.PARTIAL,
    )
    partial_net = (partial_amount * Decimal("0.975")).quantize(Decimal("0.01"))
    bank_txn = BankTransaction(
        bank_transaction_id=f"BNK-{uuid.uuid4().hex[:8].upper()}",
        date=txn_date + timedelta(days=1),
        amount=partial_net,
        description=f"Partial payment {ref_id}",
        reference=ref_id,
        account="ACC-001",
    )
    return txn, invoice, bank_txn, None


def _fee_anomaly_record(txn_id, inv_id, ref_id, customer_id, amount, fee, tax_on_fee, net, txn_date):
    """Settlement deducted an unusual fee."""
    unusual_fee = (amount * Decimal("0.035")).quantize(Decimal("0.01"))
    unusual_tax = (unusual_fee * GST_RATE).quantize(Decimal("0.01"))
    unusual_net = amount - unusual_fee - unusual_tax
    txn = Transaction(
        transaction_id=txn_id,
        customer_id=customer_id,
        amount=amount,
        payment_status=PaymentStatus.CAPTURED,
        payment_method=random.choice(PAYMENT_METHODS),
        timestamp=txn_date,
        reference_id=ref_id,
        invoice_id=inv_id,
        ground_truth_status="EXCEPTION",
    )
    invoice = Invoice(
        invoice_id=inv_id,
        customer_id=customer_id,
        invoice_amount=amount,
        tax=Decimal("0"),
        total_amount=amount,
        date=txn_date - timedelta(days=3),
        status=InvoiceStatus.PAID,
    )
    bank_txn = BankTransaction(
        bank_transaction_id=f"BNK-{uuid.uuid4().hex[:8].upper()}",
        date=txn_date + timedelta(days=random.randint(3, 7)),  # Delayed settlement
        amount=unusual_net,
        description=f"Settlement {ref_id}",
        reference=ref_id,
        account="ACC-001",
    )
    settlement = Settlement(
        settlement_id=f"SET-{uuid.uuid4().hex[:8].upper()}",
        transaction_id=txn_id,
        gross_amount=amount,
        fees=unusual_fee,
        tax=unusual_tax,
        net_amount=unusual_net,
        settlement_date=txn_date + timedelta(days=random.randint(3, 7)),
        status=SettlementStatus.PROCESSED,
    )
    return txn, invoice, bank_txn, settlement


def dataset_to_dicts(
    transactions: List[Transaction],
    invoices: List[Invoice],
    bank_transactions: List[BankTransaction],
    settlements: List[Settlement],
) -> Dict[str, List[Dict]]:
    """Convert dataset to serializable dicts."""
    from app.utils.helpers import dict_to_mongo
    return {
        "transactions": [dict_to_mongo(t) for t in transactions],
        "invoices": [dict_to_mongo(i) for i in invoices],
        "bank_transactions": [dict_to_mongo(b) for b in bank_transactions],
        "settlements": [dict_to_mongo(s) for s in settlements],
    }
