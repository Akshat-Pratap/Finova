"""Finova — Data Ingestion & Flexible Column Mapping Tests."""
from __future__ import annotations

import pytest
from app.services.data_engine.column_mapper import detect_column_mapping, apply_column_mapping
from app.services.dataset_service import DatasetService


def test_column_mapping_auto_detection():
    raw_columns = ["Payment Ref", "Gross Amount", "Payer Name", "Txn Date", "State"]
    detected = detect_column_mapping(raw_columns)

    assert detected.get("Payment Ref") == "reference_id"
    assert detected.get("Gross Amount") == "amount"
    assert detected.get("Payer Name") == "customer_id"
    assert detected.get("Txn Date") == "timestamp"


def test_apply_column_mapping():
    records = [
        {"Payment Ref": "REF-9988", "Gross Amount": "1500.50", "Payer Name": "Acme Co"},
        {"Payment Ref": "REF-9989", "Gross Amount": "2400.00", "Payer Name": "Beta Inc"},
    ]
    mapping = {"Payment Ref": "reference_id", "Gross Amount": "amount", "Payer Name": "customer_id"}
    mapped = apply_column_mapping(records, mapping)

    assert mapped[0]["reference_id"] == "REF-9988"
    assert mapped[0]["amount"] == "1500.50"
    assert mapped[0]["customer_id"] == "Acme Co"
    assert mapped[0]["_raw"]["Payment Ref"] == "REF-9988"


@pytest.mark.asyncio
async def test_dataset_upload_and_validation():
    csv_content = b"""transaction_id,amount,customer_id,timestamp,reference_id
TXN-101,500.00,CUST-001,2026-08-01T10:00:00,REF-101
TXN-102,1200.50,CUST-002,2026-08-01T11:00:00,REF-102
TXN-103,-50.00,CUST-003,2026-08-01T12:00:00,REF-103
"""
    svc = DatasetService(db=None)
    dataset, mapping, sample = await svc.upload_dataset(
        content=csv_content,
        filename="bank_statement_aug.csv",
        organization_id="org_test_1",
    )

    assert dataset.record_count == 3
    assert dataset.filename == "bank_statement_aug.csv"
    assert len(sample) == 3

    # Validate dataset
    validation_report = await svc.validate_dataset(
        dataset_id=dataset.dataset_id,
        organization_id="org_test_1",
    )

    assert validation_report["ready_for_processing"] is True
    assert validation_report["valid_count"] == 2
    assert validation_report["invalid_count"] == 1
