"""Finova — Payment Gateway & Razorpay Provider Tests."""
from __future__ import annotations

import pytest
from app.services.integrations.razorpay_provider import RazorpayProvider
from app.services.workflow_controller import WorkflowController


@pytest.mark.asyncio
async def test_razorpay_provider_mock_fetch():
    provider = RazorpayProvider()
    assert provider.mode in ("MOCK", "LIVE")

    is_connected, msg = await provider.test_connection()
    assert is_connected is True

    payments = await provider.fetch_payments(count=10)
    assert len(payments) == 10
    assert "transaction_id" in payments[0]
    assert "amount" in payments[0]
    assert "currency" in payments[0]

    settlements = await provider.fetch_settlements(count=5)
    assert len(settlements) == 5
    assert "gross_amount" in settlements[0]
    assert "net_amount" in settlements[0]


@pytest.mark.asyncio
async def test_razorpay_sync_to_reconciliation():
    provider = RazorpayProvider()
    payments = await provider.fetch_payments(count=20)
    settlements = await provider.fetch_settlements(count=5)

    controller = WorkflowController(db=None)
    run, results, analytics = await controller.run_from_data(
        txn_records=payments,
        inv_records=[],
        bank_records=[],
        sett_records=settlements,
        dataset_name="razorpay_test_sync",
        organization_id="org_test_rzp",
    )

    assert run.records_received == 20
    assert len(results) >= 20
    assert run.match_rate >= 0.0
    assert analytics is not None
