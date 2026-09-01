"""Finova — Production Reconciliation & Idempotency Tests."""
from __future__ import annotations

import pytest
from app.services.workflow_controller import WorkflowController
from app.services.background_runner import BackgroundJobRunner, JobStatus


@pytest.mark.asyncio
async def test_idempotency_run_protection():
    controller = WorkflowController(db=None)
    records = [
        {"transaction_id": "TX-1", "amount": 100.0, "customer_id": "C-1", "timestamp": "2026-08-01T00:00:00"},
        {"transaction_id": "TX-2", "amount": 200.0, "customer_id": "C-2", "timestamp": "2026-08-01T00:00:00"},
    ]

    # Run 1 with idempotency key
    run1, res1, _ = await controller.run_from_data(
        txn_records=records,
        inv_records=[],
        bank_records=[],
        sett_records=[],
        dataset_name="batch_1",
        organization_id="org_idem",
        idempotency_key="idemp_key_12345",
    )

    # Run 2 with same idempotency key
    run2, res2, _ = await controller.run_from_data(
        txn_records=records,
        inv_records=[],
        bank_records=[],
        sett_records=[],
        dataset_name="batch_1_repeat",
        organization_id="org_idem",
        idempotency_key="idemp_key_12345",
    )

    assert run1.run_id == run2.run_id


@pytest.mark.asyncio
async def test_background_job_lifecycle():
    job = BackgroundJobRunner.create_job(
        organization_id="org_bg",
        run_id="RUN-BG-101",
        description="Async Background Reconciliation",
    )

    assert job.status == JobStatus.QUEUED
    assert job.progress_percent == 0.0

    async def _dummy_task():
        job.progress_percent = 50.0
        return {"matched": 5}

    task = BackgroundJobRunner.spawn_task(job.job_id, _dummy_task)
    await task

    polled = BackgroundJobRunner.get_job(job.job_id)
    assert polled.status == JobStatus.COMPLETED
    assert polled.progress_percent == 100.0
    assert polled.result == {"matched": 5}
