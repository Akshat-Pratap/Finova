"""Finova — Tests: Data Engine."""
import pytest
from decimal import Decimal

from app.services.data_engine.cleaner import clean_transactions, _clean_amount
from app.services.data_engine.validator import validate_transactions
from app.services.data_engine.normalizer import normalize_transactions
from app.services.data_generator import generate_dataset, dataset_to_dicts


def test_clean_transactions_valid():
    records = [
        {"transaction_id": "TXN-001", "customer_id": "CUST-001", "amount": "1000", "timestamp": "2024-01-01"},
        {"transaction_id": "TXN-002", "customer_id": "CUST-002", "amount": "2500.50", "timestamp": "2024-01-02"},
    ]
    result = clean_transactions(records)
    assert result.records_cleaned == 2
    assert result.invalid_removed == 0


def test_clean_transactions_invalid_amount():
    records = [
        {"transaction_id": "TXN-001", "customer_id": "CUST-001", "amount": "not_a_number"},
    ]
    result = clean_transactions(records)
    assert result.invalid_removed == 1
    assert result.records_cleaned == 0


def test_clean_transactions_duplicate_ids():
    records = [
        {"transaction_id": "TXN-001", "customer_id": "CUST-001", "amount": "1000", "timestamp": "2024-01-01"},
        {"transaction_id": "TXN-001", "customer_id": "CUST-001", "amount": "1000", "timestamp": "2024-01-01"},
    ]
    result = clean_transactions(records)
    assert result.records_cleaned == 1
    assert result.duplicates_removed == 1


def test_clean_transactions_missing_required_fields():
    records = [
        {"customer_id": "CUST-001", "amount": "1000"},  # Missing transaction_id
    ]
    result = clean_transactions(records)
    # Missing transaction_id gets removed
    assert result.invalid_removed == 1


def test_clean_amount_valid():
    val, err = _clean_amount("1500.00")
    assert val == Decimal("1500.00")
    assert err is None


def test_clean_amount_negative():
    val, err = _clean_amount("-100")
    assert val is None
    assert err is not None


def test_clean_amount_invalid():
    val, err = _clean_amount("abc")
    assert val is None
    assert err is not None


def test_normalize_transactions():
    records = [
        {
            "transaction_id": "TXN-001",
            "customer_id": "CUST-001",
            "amount": "5000",
            "timestamp": "2024-01-15",
            "reference_id": "REF-ABC",
            "payment_status": "captured",
        }
    ]
    txns, errors = normalize_transactions(records, "RUN-001")
    assert len(txns) == 1
    assert errors == []
    assert txns[0].transaction_id == "TXN-001"
    assert txns[0].amount == Decimal("5000")


def test_validate_transactions_valid():
    from datetime import datetime
    txns, errors = normalize_transactions(
        [{"transaction_id": "TXN-001", "customer_id": "CUST-001", "amount": "1000", "timestamp": "2024-01-01"}],
        "RUN-001"
    )
    valid, report = validate_transactions(txns)
    assert report.records_valid == 1
    assert report.records_invalid == 0


def test_validate_transactions_zero_amount():
    records = [{"transaction_id": "TXN-001", "customer_id": "CUST-001", "amount": "0", "timestamp": "2024-01-01"}]
    txns, _ = normalize_transactions(records, "RUN-001")
    valid, report = validate_transactions(txns)
    assert report.records_invalid == 1


def test_synthetic_data_generation():
    txns, invs, banks, settlements = generate_dataset(num_records=50, seed=123)
    assert len(txns) == 50
    assert len(invs) > 0
    # All transactions have amounts > 0
    for txn in txns:
        assert txn.amount > 0
    # All have ground truth labels
    for txn in txns:
        assert txn.ground_truth_status in ("MATCH", "MISMATCH", "DUPLICATE", "EXCEPTION")


def test_synthetic_data_anomaly_distribution():
    """Verify anomaly distribution is roughly correct."""
    txns, _, _, _ = generate_dataset(num_records=200, seed=42)
    clean = sum(1 for t in txns if t.ground_truth_status == "MATCH")
    assert clean > 100, f"Expected >100 clean matches, got {clean}"
