"""Finova — Financial Report Export Tests."""
from __future__ import annotations

import json
from decimal import Decimal
from app.services.report_generator import generate_csv_report, generate_json_report


def test_generate_csv_report():
    records = [
        {"transaction_id": "TXN-001", "customer_id": "CUST-A", "amount": Decimal("1500.00"), "status": "MATCHED"},
        {"transaction_id": "TXN-002", "customer_id": "CUST-B", "amount": Decimal("320.50"), "status": "MISMATCH"},
    ]
    csv_out = generate_csv_report(records)
    lines = csv_out.strip().split("\r\n") if "\r\n" in csv_out else csv_out.strip().split("\n")
    assert len(lines) == 3
    assert "transaction_id,customer_id,amount,status" in lines[0]
    assert "TXN-001,CUST-A,1500.00,MATCHED" in lines[1]


def test_generate_json_report():
    records = [
        {"exception_id": "EX-001", "type": "AMOUNT_MISMATCH", "difference": 50.0},
    ]
    json_out = generate_json_report(records, metadata={"org": "test_org"})
    parsed = json.loads(json_out)
    assert parsed["record_count"] == 1
    assert parsed["metadata"]["org"] == "test_org"
    assert parsed["records"][0]["exception_id"] == "EX-001"
