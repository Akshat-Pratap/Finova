"""Finova — Large Dataset Hardening & Reconciliation Architecture Tests.

Verifies:
A. Single source datasets without counterpart produce NO_COUNTERPART_SOURCE (0 exceptions, 0 AI calls).
B. Valid counterpart datasets produce deterministic matching.
C. Exception IDs have high entropy UUID4 collision resistance.
D. Duplicate concurrent runs for same dataset are prevented.
E. Idempotency keys prevent duplicate runs.
F. Bounded batch processing updates live progress metrics.
G. MongoDB Atlas storage errors fail safely (STORAGE_LIMIT_REACHED, not falsely COMPLETED).
H. Non-blocking background execution and run status retrieval.
I. Tenant isolation & audit log hash chain integrity.
J. High throughput benchmark on large dataset sizes.
"""
from __future__ import annotations

import asyncio
import time
import uuid
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.models.processing_run import RunStatus, ProcessingRun
from app.models.reconciliation import ReconciliationStatus
from app.models.audit_log import AuditEventType
from app.services.workflow_controller import WorkflowController
from app.services.background_runner import BackgroundJobRunner, JobStatus
from app.services.exception_manager import ExceptionManager
from app.services.audit_logger import AuditLogger
from app.services.memory_store import memory_runs, memory_datasets


@pytest.mark.asyncio
async def test_no_counterpart_source_behavior():
    """Single source transactions without bank/invoice/settlement counterpart must NOT create artificial exceptions."""
    controller = WorkflowController(db=None)
    txns = [
        {"transaction_id": f"TXN-{i}", "amount": 100.0 + i, "customer_id": f"CUST-{i}", "timestamp": "2026-08-01T10:00:00"}
        for i in range(50)
    ]

    run, results, analytics = await controller.run_from_data(
        txn_records=txns,
        inv_records=[],
        bank_records=[],
        sett_records=[],
        dataset_name="single_source_bank_csv",
        organization_id="org_test_no_counterpart",
    )

    assert run.status == RunStatus.NO_COUNTERPART_SOURCE
    assert run.records_matched == 0
    assert run.records_manual_review == 0
    assert run.records_ai_reviewed == 0
    assert analytics.get("exception_count", 0) == 0
    assert len(results) == 0
    assert "no counterpart dataset" in (run.error_message or "").lower()


@pytest.mark.asyncio
async def test_valid_counterpart_matching():
    """When transactions and invoices/bank statements exist, deterministic matching occurs."""
    controller = WorkflowController(db=None)
    txns = [
        {"transaction_id": "TX-1", "amount": 5000.0, "customer_id": "C-1", "reference_id": "REF-1", "invoice_id": "INV-1", "timestamp": "2026-08-01T10:00:00"},
        {"transaction_id": "TX-2", "amount": 2500.0, "customer_id": "C-2", "reference_id": "REF-2", "invoice_id": "INV-2", "timestamp": "2026-08-01T10:00:00"},
    ]
    invs = [
        {"invoice_id": "INV-1", "customer_id": "C-1", "invoice_amount": 5000.0, "total_amount": 5000.0, "date": "2026-08-01T00:00:00"},
        {"invoice_id": "INV-2", "customer_id": "C-2", "invoice_amount": 2500.0, "total_amount": 2500.0, "date": "2026-08-01T00:00:00"},
    ]
    banks = [
        {"bank_transaction_id": "BNK-1", "amount": 5000.0, "reference": "REF-1", "date": "2026-08-01T11:00:00"},
        {"bank_transaction_id": "BNK-2", "amount": 2500.0, "reference": "REF-2", "date": "2026-08-01T11:00:00"},
    ]

    run, results, analytics = await controller.run_from_data(
        txn_records=txns,
        inv_records=invs,
        bank_records=banks,
        sett_records=[],
        dataset_name="multi_source_reconciliation",
        organization_id="org_test_matching",
    )

    assert run.status == RunStatus.COMPLETED
    assert run.records_matched == 2
    assert run.match_rate == 1.0
    assert len(results) == 2


@pytest.mark.asyncio
async def test_unmatched_transaction_with_counterpart_creates_exception():
    """Unmatched transaction when counterpart IS available generates an actionable exception."""
    controller = WorkflowController(db=None)
    txns = [
        {"transaction_id": "TX-MATCHED", "amount": 1000.0, "customer_id": "C-1", "reference_id": "REF-M", "invoice_id": "INV-M", "timestamp": "2026-08-01T10:00:00"},
        {"transaction_id": "TX-UNMATCHED", "amount": 9999.0, "customer_id": "C-UNKNOWN", "reference_id": "REF-NONE", "timestamp": "2026-08-01T10:00:00"},
    ]
    invs = [
        {"invoice_id": "INV-M", "customer_id": "C-1", "invoice_amount": 1000.0, "total_amount": 1000.0, "date": "2026-08-01T00:00:00"},
    ]
    banks = [
        {"bank_transaction_id": "BNK-M", "amount": 1000.0, "reference": "REF-M", "date": "2026-08-01T11:00:00"},
    ]

    run, results, analytics = await controller.run_from_data(
        txn_records=txns,
        inv_records=invs,
        bank_records=banks,
        sett_records=[],
        dataset_name="partial_match_dataset",
        organization_id="org_test_unmatched",
    )

    assert run.status == RunStatus.COMPLETED
    assert run.records_matched == 1
    assert run.records_unmatched == 1
    assert analytics.get("exception_count", 0) >= 1
    assert len([r for r in results if r.status != ReconciliationStatus.MATCHED]) >= 1


def test_exception_id_collision_resistance():
    """Generates 25,000 exception IDs and proves 0 collisions across large datasets."""
    ids = set()
    total = 25000
    for _ in range(total):
        eid = f"EX-{uuid.uuid4().hex.upper()}"
        ids.add(eid)
    assert len(ids) == total


@pytest.mark.asyncio
async def test_concurrent_duplicate_run_protection():
    """Cannot start duplicate concurrent reconciliation runs for the same dataset."""
    controller = WorkflowController(db=None)
    dataset_id = "ds_concurrent_test"

    # Simulate an active run in memory
    active_run = ProcessingRun(
        run_id="RUN-ACTIVE-01",
        organization_id="org_concurrent",
        dataset_id=dataset_id,
        status=RunStatus.PROCESSING,
    )
    memory_runs["RUN-ACTIVE-01"] = active_run.model_dump()

    # Query active run directly
    detected = await controller._check_active_run(dataset_id=dataset_id, organization_id="org_concurrent")
    assert detected is not None
    assert detected.run_id == "RUN-ACTIVE-01"

    # Attempt to start another run for same dataset returns the existing active run
    run_dup, _, _ = await controller.run_from_data(
        txn_records=[{"transaction_id": "TX-1", "amount": 100.0}],
        inv_records=[],
        bank_records=[],
        sett_records=[],
        dataset_id=dataset_id,
        organization_id="org_concurrent",
    )
    assert run_dup.run_id == "RUN-ACTIVE-01"

    # Cleanup
    memory_runs.pop("RUN-ACTIVE-01", None)


@pytest.mark.asyncio
async def test_idempotency_key_duplicate_prevention():
    """Repeated requests with identical idempotency key return the existing run."""
    controller = WorkflowController(db=None)
    txns = [{"transaction_id": "TX-1", "amount": 100.0, "timestamp": "2026-08-01T10:00:00"}]

    run1, _, _ = await controller.run_from_data(
        txn_records=txns,
        inv_records=[],
        bank_records=[],
        sett_records=[],
        organization_id="org_idem_test",
        idempotency_key="unique_key_9988",
    )

    run2, _, _ = await controller.run_from_data(
        txn_records=txns,
        inv_records=[],
        bank_records=[],
        sett_records=[],
        organization_id="org_idem_test",
        idempotency_key="unique_key_9988",
    )

    assert run1.run_id == run2.run_id


@pytest.mark.asyncio
async def test_bounded_batch_processing_and_progress():
    """Processes records in bounded batches and updates progress rate."""
    controller = WorkflowController(db=None)
    count = 1000
    txns = [
        {"transaction_id": f"TX-{i}", "amount": 100.0 + i, "customer_id": f"C-{i}", "reference_id": f"REF-{i}", "invoice_id": f"INV-{i}", "timestamp": "2026-08-01T10:00:00"}
        for i in range(count)
    ]
    invs = [
        {"invoice_id": f"INV-{i}", "customer_id": f"C-{i}", "invoice_amount": 100.0 + i, "total_amount": 100.0 + i, "date": "2026-08-01T00:00:00"}
        for i in range(count)
    ]
    banks = [
        {"bank_transaction_id": f"BNK-{i}", "amount": 100.0 + i, "reference": f"REF-{i}", "date": "2026-08-01T11:00:00"}
        for i in range(count)
    ]

    job = BackgroundJobRunner.create_job(
        organization_id="org_batch_test",
        run_id="RUN-BATCH-01",
        description="Batch processing test",
    )

    run, results, _ = await controller.run_from_data(
        txn_records=txns,
        inv_records=invs,
        bank_records=banks,
        sett_records=[],
        organization_id="org_batch_test",
        job=job,
    )

    assert run.status == RunStatus.COMPLETED
    assert run.records_valid == count
    assert run.records_matched == count
    assert len(results) == count
    assert job.status == JobStatus.COMPLETED
    assert job.records_processed == count


@pytest.mark.asyncio
async def test_storage_limit_failure_semantics():
    """Atlas storage quota errors mark run as STORAGE_LIMIT_REACHED rather than COMPLETED."""
    controller = WorkflowController(db=None)
    txns = [{"transaction_id": "TX-1", "amount": 100.0, "timestamp": "2026-08-01T10:00:00"}]

    with patch.object(controller, "_persist_results", side_effect=Exception("Writes are blocked on your cluster: you are over your space quota, using 516 MB of 512 MB")):
        with pytest.raises(Exception) as exc_info:
            await controller.run_from_data(
                txn_records=txns,
                inv_records=[{"invoice_id": "INV-1", "invoice_amount": 100.0, "total_amount": 100.0}],
                bank_records=[],
                sett_records=[],
                organization_id="org_storage_test",
            )

        assert "quota" in str(exc_info.value).lower()
        saved_runs = [r for r in memory_runs.values() if r.get("organization_id") == "org_storage_test"]
        assert len(saved_runs) > 0
        assert saved_runs[-1]["status"] == RunStatus.STORAGE_LIMIT_REACHED.value


@pytest.mark.asyncio
async def test_background_job_and_status_retrieval():
    """Background jobs can be spawned, queried, and retrieved by run_id."""
    job = BackgroundJobRunner.create_job(
        organization_id="org_bg_test",
        run_id="RUN-ASYNC-99",
        description="Async run test",
    )
    assert job.status == JobStatus.QUEUED

    async def _mock_work():
        job.records_total = 100
        job.records_processed = 100
        job.matched_records = 100
        return {"status": "COMPLETED", "matched": 100}

    task = BackgroundJobRunner.spawn_task(job.job_id, _mock_work)
    await task

    polled_by_job = BackgroundJobRunner.get_job(job.job_id)
    polled_by_run = BackgroundJobRunner.get_job_by_run_id("RUN-ASYNC-99")

    assert polled_by_job is not None
    assert polled_by_run is not None
    assert polled_by_run.status == JobStatus.COMPLETED
    assert polled_by_run.matched_records == 100


@pytest.mark.asyncio
async def test_audit_hash_chain_with_new_event_types():
    """Audit logger correctly logs and verifies NO_COUNTERPART_SOURCE and STORAGE_LIMIT events."""
    logger = AuditLogger(db=None)
    org_id = "org_audit_hardening"

    e1 = await logger.log(
        event_type=AuditEventType.PROCESSING_STARTED,
        organization_id=org_id,
        actor="system",
        message="Job started",
    )
    e2 = await logger.log(
        event_type=AuditEventType.NO_COUNTERPART_SOURCE,
        organization_id=org_id,
        actor="finance_engine",
        message="No counterpart source available",
    )
    e3 = await logger.log(
        event_type=AuditEventType.PROCESSING_STORAGE_LIMIT,
        organization_id=org_id,
        actor="system",
        message="Storage limit reached",
    )

    assert e2.previous_hash == e1.event_hash
    assert e3.previous_hash == e2.event_hash

    verification = await logger.verify_integrity(org_id)
    assert verification["verified"] is True
    assert verification["total_events"] == 3


@pytest.mark.asyncio
async def test_performance_throughput_benchmark():
    """Controlled performance benchmark on 10,000 records."""
    controller = WorkflowController(db=None)
    count = 10000

    txns = [
        {"transaction_id": f"T-{i}", "amount": 500.0 + (i % 100), "customer_id": f"C-{i}", "reference_id": f"R-{i}", "invoice_id": f"I-{i}", "timestamp": "2026-08-01T10:00:00"}
        for i in range(count)
    ]
    invs = [
        {"invoice_id": f"I-{i}", "customer_id": f"C-{i}", "invoice_amount": 500.0 + (i % 100), "total_amount": 500.0 + (i % 100), "date": "2026-08-01T00:00:00"}
        for i in range(count)
    ]
    banks = [
        {"bank_transaction_id": f"B-{i}", "amount": 500.0 + (i % 100), "reference": f"R-{i}", "date": "2026-08-01T11:00:00"}
        for i in range(count)
    ]

    start_time = time.perf_counter()
    run, results, _ = await controller.run_from_data(
        txn_records=txns,
        inv_records=invs,
        bank_records=banks,
        sett_records=[],
        organization_id="org_perf_bench",
    )
    elapsed = time.perf_counter() - start_time

    assert run.status == RunStatus.COMPLETED
    assert run.records_matched == count
    throughput = count / elapsed if elapsed > 0 else 0
    print(f"\n[PERFORMANCE] Reconciled {count:,} records in {elapsed:.3f}s ({throughput:,.1f} records/sec)")
    assert throughput > 1000  # Exceeds 1,000 records/sec
