"""Finova — Workflow Controller.

Central orchestrator that coordinates the entire reconciliation pipeline:
Data Engine → Finance Engine → AI Engine → Exception Manager → Analytics → Audit Log
With multi-tenancy, background jobs, idempotency, and large dataset streaming.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.models.audit_log import AuditEventType
from app.models.dataset import DatasetStatus
from app.models.processing_run import ProcessingRun, RunStatus
from app.models.reconciliation import ReconciliationResult, ReconciliationStatus
from app.services.background_runner import JobStatus
from app.services.analytics_engine import compute_run_analytics
from app.services.audit_logger import AuditLogger
from app.services.exception_manager import ExceptionManager
from app.services.ai_engine.investigator import investigate_transaction
from app.services.data_engine.ingestion import ingest_synthetic, IngestionResult
from app.services.data_engine.column_mapper import apply_column_mapping
from app.services.data_engine.cleaner import (
    clean_transactions, clean_invoices, clean_bank_transactions, clean_settlements,
)
from app.services.data_engine.normalizer import (
    normalize_transactions, normalize_invoices,
    normalize_bank_transactions, normalize_settlements,
)
from app.services.data_engine.validator import validate_transactions
from app.services.finance_engine.duplicate_detector import detect_duplicates
from app.services.finance_engine.reconciliation import reconcile_batch
from app.services.memory_store import memory_runs, memory_results
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)

# Backwards-compatible aliases
_memory_runs = memory_runs
_memory_results = memory_results


class WorkflowController:
    """Orchestrates the complete Finova reconciliation workflow."""

    def __init__(self, db=None):
        self._db = db
        self._audit = AuditLogger(db)
        self._exceptions = ExceptionManager(db)

    async def run_synthetic(
        self,
        num_records: int = 250,
        seed: int = 42,
        organization_id: str = "org_default",
    ) -> Tuple[ProcessingRun, List[ReconciliationResult], Dict[str, Any]]:
        """
        Run full reconciliation on a synthetic dataset.
        Returns (processing_run, results, analytics).
        """
        run = ProcessingRun(
            run_id=f"RUN-{uuid.uuid4().hex[:12].upper()}",
            organization_id=organization_id,
            dataset_source="synthetic",
            dataset_name=f"synthetic_{num_records}_{seed}",
            records_total=num_records,
        )

        start_time = time.perf_counter()

        await self._audit.log(
            event_type=AuditEventType.PROCESSING_STARTED,
            organization_id=organization_id,
            processing_run_id=run.run_id,
            message=f"Processing started: synthetic dataset ({num_records} records, seed={seed})",
        )

        try:
            # Step 1: Ingest
            ingestion = ingest_synthetic(num_records=num_records, seed=seed)
            txn_raw = ingestion.get("transactions", IngestionResult()).records
            inv_raw = ingestion.get("invoices", IngestionResult()).records
            bank_raw = ingestion.get("bank_transactions", IngestionResult()).records
            sett_raw = ingestion.get("settlements", IngestionResult()).records

            run.records_received = len(txn_raw)
            run.records_total = len(txn_raw)

            # Step 2: Clean
            txn_cleaned = clean_transactions(txn_raw)
            inv_cleaned = clean_invoices(inv_raw)
            bank_cleaned = clean_bank_transactions(bank_raw)
            sett_cleaned = clean_settlements(sett_raw)

            run.records_invalid = txn_cleaned.invalid_removed
            run.duplicates_input = txn_cleaned.duplicates_removed

            # Step 3: Normalize
            transactions, norm_errors = normalize_transactions(
                txn_cleaned.records,
                processing_run_id=run.run_id,
                organization_id=organization_id,
            )
            invoices, _ = normalize_invoices(inv_cleaned.records, run.run_id, organization_id)
            bank_txns, _ = normalize_bank_transactions(bank_cleaned.records, run.run_id, organization_id)
            settlements, _ = normalize_settlements(sett_cleaned.records, run.run_id, organization_id)

            # Step 4: Validate
            valid_txns, validation_report = validate_transactions(
                transactions, txn_cleaned.duplicates_removed
            )
            run.records_valid = validation_report.records_valid

            await self._audit.log(
                AuditEventType.DATASET_GENERATED,
                organization_id=organization_id,
                processing_run_id=run.run_id,
                message=f"{run.records_valid} records validated ({run.records_invalid} invalid)",
                metadata=validation_report.to_dict(),
            )

            # Step 5: Duplicate detection
            unique_txns, duplicate_ids = detect_duplicates(valid_txns)

            # Step 6: Reconciliation
            run.status = RunStatus.PROCESSING
            results = reconcile_batch(
                transactions=unique_txns,
                invoices=invoices,
                bank_transactions=bank_txns,
                settlements=settlements,
                processing_run_id=run.run_id,
                duplicate_ids=duplicate_ids,
            )

            for r in results:
                r.organization_id = organization_id

            # Add DUPLICATE results for detected duplicates
            for txn in valid_txns:
                if txn.transaction_id in duplicate_ids:
                    dup_result = ReconciliationResult(
                        processing_run_id=run.run_id,
                        organization_id=organization_id,
                        transaction_id=txn.transaction_id,
                        customer_id=txn.customer_id,
                        status=ReconciliationStatus.DUPLICATE,
                        confidence=0.95,
                        decision_source="AUTOMATED_RULE",
                        reason="Transaction flagged as duplicate.",
                        ground_truth_status=txn.ground_truth_status,
                    )
                    results.append(dup_result)

            # Step 7: AI investigation for ambiguous cases
            ai_results = await self._run_ai_investigations(
                results=results,
                transactions={t.transaction_id: t for t in valid_txns},
                invoices={i.invoice_id: i for i in invoices},
                bank_txns={b.bank_transaction_id: b for b in bank_txns},
                settlements={s.transaction_id: s for s in settlements},
                processing_run_id=run.run_id,
                organization_id=organization_id,
            )
            results = ai_results

            # Step 8: Create exceptions
            await self._create_exceptions(results, run.run_id, organization_id)

            # Step 9: Persist results
            await self._persist_results(results)

            # Step 10: Finalize run metrics
            elapsed = time.perf_counter() - start_time
            run.processing_time_seconds = round(elapsed, 3)
            run.elapsed_seconds = run.processing_time_seconds
            run.records_processed = len(results)
            run.progress_percent = 100.0
            run.processing_rate = round(len(results) / max(0.001, elapsed), 1)
            run.records_matched = sum(1 for r in results if r.status == ReconciliationStatus.MATCHED)
            run.records_ai_reviewed = sum(1 for r in results if r.ai_investigated)
            run.records_manual_review = sum(1 for r in results if r.status == ReconciliationStatus.MANUAL_REVIEW)
            run.records_mismatch = sum(1 for r in results if r.status == ReconciliationStatus.MISMATCH)
            run.records_duplicate = sum(1 for r in results if r.status == ReconciliationStatus.DUPLICATE)
            run.records_missing = sum(1 for r in results if r.status == ReconciliationStatus.MISSING)
            run.records_unmatched = len(results) - run.records_matched
            run.match_rate = round(run.records_matched / len(results), 4) if results else 0.0
            run.average_confidence = round(
                sum(r.confidence for r in results) / len(results), 4
            ) if results else 0.0
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()

            # Analytics
            analytics = compute_run_analytics(results, run)
            if "precision" in analytics:
                run.precision = analytics["precision"]
                run.recall = analytics["recall"]
                run.f1_score = analytics["f1_score"]

            await self._audit.log(
                AuditEventType.PROCESSING_COMPLETED,
                organization_id=organization_id,
                processing_run_id=run.run_id,
                message=(
                    f"Completed: {run.records_matched} matched, "
                    f"{run.records_ai_reviewed} AI reviewed, "
                    f"{run.exceptions_created} exceptions in {elapsed:.2f}s"
                ),
                metadata={
                    "match_rate": run.match_rate,
                    "average_confidence": run.average_confidence,
                },
            )

            await self._persist_run(run)

        except Exception as exc:
            run.status = RunStatus.FAILED
            run.error_message = str(exc)
            run.completed_at = datetime.utcnow()
            logger.error("Processing run failed: %s", exc, exc_info=True)
            await self._audit.log(
                AuditEventType.PROCESSING_COMPLETED,
                organization_id=organization_id,
                processing_run_id=run.run_id,
                message=f"Processing FAILED: {exc}",
            )
            await self._persist_run(run)
            raise

        return run, results, analytics

    async def run_from_data(
        self,
        txn_records: list,
        inv_records: list,
        bank_records: list,
        sett_records: list,
        dataset_name: str = "uploaded",
        organization_id: str = "org_default",
        dataset_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        triggered_by: Optional[str] = None,
        job: Optional[Any] = None,
    ) -> Tuple[ProcessingRun, List[ReconciliationResult], Dict[str, Any]]:
        """Run reconciliation on uploaded or imported raw data with bounded batching and counterpart checks."""
        # 1. Idempotency check
        if idempotency_key:
            existing = await self._check_idempotency(idempotency_key, organization_id)
            if existing:
                logger.info("Idempotent request returning existing run: %s", existing.run_id)
                results = await self.get_results_for_run(existing.run_id, organization_id)
                analytics = compute_run_analytics(results, existing)
                return existing, results, analytics

        # 2. Concurrency check for active run on same dataset
        if dataset_id:
            active_run = await self._check_active_run(dataset_id, organization_id)
            if active_run:
                logger.warning(
                    "Duplicate run requested for dataset %s while run %s is active (%s)",
                    dataset_id,
                    active_run.run_id,
                    active_run.status.value,
                )
                results = await self.get_results_for_run(active_run.run_id, organization_id)
                analytics = compute_run_analytics(results, active_run)
                return active_run, results, analytics

        run = ProcessingRun(
            run_id=f"RUN-{uuid.uuid4().hex[:12].upper()}",
            organization_id=organization_id,
            dataset_id=dataset_id,
            dataset_source="uploaded" if not dataset_name.startswith("razorpay") else "razorpay",
            dataset_name=dataset_name,
            idempotency_key=idempotency_key,
            triggered_by=triggered_by,
            records_total=len(txn_records),
            status=RunStatus.STARTED,
        )
        start_time = time.perf_counter()

        if job:
            job.records_total = len(txn_records)
            job.progress_percent = 5.0

        await self._persist_run(run)

        await self._audit.log(
            AuditEventType.PROCESSING_STARTED,
            organization_id=organization_id,
            processing_run_id=run.run_id,
            actor=triggered_by or "system",
            actor_id=triggered_by,
            message=f"Processing {len(txn_records)} records for organization {organization_id}",
        )

        try:
            # 3. Check for Counterpart Availability
            has_counterpart = bool(inv_records or bank_records or sett_records)

            if not has_counterpart and self._db is not None:
                try:
                    inv_count = await self._db.invoices.count_documents({"organization_id": organization_id}, limit=1)
                    bank_count = await self._db.bank_transactions.count_documents({"organization_id": organization_id}, limit=1)
                    sett_count = await self._db.settlements.count_documents({"organization_id": organization_id}, limit=1)
                    has_counterpart = bool(inv_count > 0 or bank_count > 0 or sett_count > 0)
                except Exception as exc:
                    logger.warning("Failed to check DB counterpart records: %s", exc)

            if not has_counterpart:
                # No counterpart dataset exists: Do NOT fabricate artificial exceptions or invoke AI
                msg = (
                    f"Reconciliation cannot be performed because no counterpart dataset is available. "
                    f"This dataset contains {len(txn_records)} transactions. "
                    f"Upload or map a bank, invoice, settlement, or other compatible counterpart source to perform reconciliation."
                )
                logger.info("Dataset %s has NO_COUNTERPART_SOURCE (%d transactions)", dataset_id or dataset_name, len(txn_records))
                run.status = RunStatus.NO_COUNTERPART_SOURCE
                run.error_message = msg
                run.records_total = len(txn_records)
                run.records_received = len(txn_records)
                run.records_valid = len(txn_records)
                run.records_processed = 0
                run.records_matched = 0
                run.records_unmatched = 0
                run.records_missing = 0
                run.exceptions_created = 0
                run.match_rate = 0.0
                run.average_confidence = 0.0
                run.progress_percent = 100.0
                run.processing_time_seconds = round(time.perf_counter() - start_time, 3)
                run.elapsed_seconds = run.processing_time_seconds
                run.completed_at = datetime.utcnow()

                await self._persist_run(run)

                await self._audit.log(
                    AuditEventType.NO_COUNTERPART_SOURCE,
                    organization_id=organization_id,
                    processing_run_id=run.run_id,
                    actor=triggered_by or "system",
                    actor_id=triggered_by,
                    message=msg,
                    metadata={"records_total": len(txn_records), "dataset_id": dataset_id},
                )

                if job:
                    job.status = JobStatus.NO_COUNTERPART_SOURCE
                    job.progress_percent = 100.0
                    job.records_total = len(txn_records)
                    job.records_processed = 0
                    job.matched_records = 0
                    job.unmatched_records = 0
                    job.exception_count = 0
                    job.elapsed_seconds = run.processing_time_seconds
                    job.error = msg
                    job.result = {
                        "run_id": run.run_id,
                        "status": RunStatus.NO_COUNTERPART_SOURCE.value,
                        "message": msg,
                        "records_total": len(txn_records),
                        "records_processed": 0,
                        "records_matched": 0,
                        "match_rate": 0.0,
                        "exceptions_created": 0,
                    }

                analytics = {
                    "total_records": len(txn_records),
                    "matched_count": 0,
                    "unmatched_count": 0,
                    "exception_count": 0,
                    "match_rate": 0.0,
                    "status": RunStatus.NO_COUNTERPART_SOURCE.value,
                    "message": msg,
                }
                return run, [], analytics

            # 4. Clean and Normalize
            txn_cleaned = clean_transactions(txn_records)
            inv_cleaned = clean_invoices(inv_records)
            bank_cleaned = clean_bank_transactions(bank_records)
            sett_cleaned = clean_settlements(sett_records)

            run.records_total = len(txn_records)
            run.records_received = len(txn_records)
            run.records_invalid = txn_cleaned.invalid_removed
            run.duplicates_input = txn_cleaned.duplicates_removed

            transactions, _ = normalize_transactions(
                txn_cleaned.records,
                processing_run_id=run.run_id,
                organization_id=organization_id,
                dataset_id=dataset_id,
            )
            invoices, _ = normalize_invoices(inv_cleaned.records, run.run_id, organization_id)
            bank_txns, _ = normalize_bank_transactions(bank_cleaned.records, run.run_id, organization_id)
            settlements, _ = normalize_settlements(sett_cleaned.records, run.run_id, organization_id)

            valid_txns, validation_report = validate_transactions(transactions)
            run.records_valid = validation_report.records_valid
            total_valid = len(valid_txns)

            unique_txns, duplicate_ids = detect_duplicates(valid_txns)

            # 5. Process in Bounded Batches
            batch_size = max(100, getattr(settings, "reconciliation_batch_size", 1000))
            all_results: List[ReconciliationResult] = []
            processed_count = 0

            invoices_dict = {i.invoice_id: i for i in invoices}
            bank_txns_dict = {b.bank_transaction_id: b for b in bank_txns}
            settlements_dict = {s.transaction_id: s for s in settlements}

            run.status = RunStatus.PROCESSING

            for i in range(0, total_valid, batch_size):
                chunk = unique_txns[i : i + batch_size]
                chunk_results = reconcile_batch(
                    transactions=chunk,
                    invoices=invoices,
                    bank_transactions=bank_txns,
                    settlements=settlements,
                    processing_run_id=run.run_id,
                    duplicate_ids=duplicate_ids,
                )

                for r in chunk_results:
                    r.organization_id = organization_id
                    r.dataset_id = dataset_id

                for txn in chunk:
                    if txn.transaction_id in duplicate_ids:
                        chunk_results.append(
                            ReconciliationResult(
                                processing_run_id=run.run_id,
                                organization_id=organization_id,
                                dataset_id=dataset_id,
                                transaction_id=txn.transaction_id,
                                customer_id=txn.customer_id,
                                status=ReconciliationStatus.DUPLICATE,
                                confidence=0.95,
                                decision_source="AUTOMATED_RULE",
                                reason="Duplicate transaction detected.",
                            )
                        )

                # Bounded AI investigations on ambiguous chunk records
                chunk_ai_results = await self._run_ai_investigations(
                    results=chunk_results,
                    transactions={t.transaction_id: t for t in chunk},
                    invoices=invoices_dict,
                    bank_txns=bank_txns_dict,
                    settlements=settlements_dict,
                    processing_run_id=run.run_id,
                    organization_id=organization_id,
                )

                # Incrementally create exceptions and persist results
                await self._create_exceptions(chunk_ai_results, run.run_id, organization_id)
                await self._persist_results(chunk_ai_results)

                all_results.extend(chunk_ai_results)
                processed_count += len(chunk)

                # Update live progress metrics
                elapsed_now = time.perf_counter() - start_time
                run.records_processed = processed_count
                run.progress_percent = round((processed_count / max(1, total_valid)) * 100.0, 1)
                run.elapsed_seconds = round(elapsed_now, 2)
                run.processing_rate = round(processed_count / max(0.001, elapsed_now), 1)

                if job:
                    job.records_total = total_valid
                    job.records_processed = processed_count
                    job.progress_percent = run.progress_percent
                    job.matched_records = sum(1 for r in all_results if r.status == ReconciliationStatus.MATCHED)
                    job.unmatched_records = sum(1 for r in all_results if r.status in [ReconciliationStatus.MISMATCH, ReconciliationStatus.MISSING, ReconciliationStatus.MANUAL_REVIEW])
                    job.exception_count = sum(1 for r in all_results if r.status != ReconciliationStatus.MATCHED)
                    job.processing_rate = run.processing_rate
                    job.elapsed_seconds = run.elapsed_seconds

                if i % (batch_size * 2) == 0:
                    await self._persist_run(run)

            results = all_results
            elapsed = time.perf_counter() - start_time
            run.processing_time_seconds = round(elapsed, 3)
            run.elapsed_seconds = run.processing_time_seconds
            run.records_processed = len(results)
            run.progress_percent = 100.0
            run.processing_rate = round(len(results) / max(0.001, elapsed), 1)
            run.records_matched = sum(1 for r in results if r.status == ReconciliationStatus.MATCHED)
            run.records_ai_reviewed = sum(1 for r in results if r.ai_investigated)
            run.records_manual_review = sum(1 for r in results if r.status == ReconciliationStatus.MANUAL_REVIEW)
            run.records_duplicate = sum(1 for r in results if r.status == ReconciliationStatus.DUPLICATE)
            run.records_mismatch = sum(1 for r in results if r.status == ReconciliationStatus.MISMATCH)
            run.records_missing = sum(1 for r in results if r.status == ReconciliationStatus.MISSING)
            run.records_unmatched = len(results) - run.records_matched
            run.match_rate = round(run.records_matched / len(results), 4) if results else 0.0
            run.average_confidence = round(
                sum(r.confidence for r in results) / len(results), 4
            ) if results else 0.0
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()

            analytics = compute_run_analytics(results, run)
            await self._persist_run(run)

            await self._audit.log(
                AuditEventType.PROCESSING_COMPLETED,
                organization_id=organization_id,
                processing_run_id=run.run_id,
                actor=triggered_by or "system",
                message=f"Reconciliation completed in {elapsed:.2f}s: {run.records_matched} matched.",
                metadata={"match_rate": run.match_rate, "records_processed": len(results)},
            )

            if job:
                job.status = JobStatus.COMPLETED
                job.progress_percent = 100.0
                job.records_processed = len(results)
                job.matched_records = run.records_matched
                job.unmatched_records = run.records_unmatched
                job.result = {
                    "run_id": run.run_id,
                    "status": RunStatus.COMPLETED.value,
                    "records_processed": len(results),
                    "records_matched": run.records_matched,
                    "match_rate": run.match_rate,
                    "analytics": analytics,
                }

        except Exception as exc:
            err_str = str(exc)
            is_storage_limit = "over your space quota" in err_str or "AtlasError" in err_str or "8000" in err_str
            if is_storage_limit:
                run.status = RunStatus.STORAGE_LIMIT_REACHED
                run.error_message = f"Database storage quota reached: {exc}"
                logger.error("Reconciliation run halted: STORAGE_LIMIT_REACHED (%s)", exc)
                try:
                    await self._audit.log(
                        AuditEventType.PROCESSING_STORAGE_LIMIT,
                        organization_id=organization_id,
                        processing_run_id=run.run_id,
                        message=f"Storage limit exceeded: {exc}",
                    )
                except Exception:
                    pass
            else:
                run.status = RunStatus.FAILED
                run.error_message = err_str
                logger.error("Reconciliation run failed: %s", exc, exc_info=True)

            run.completed_at = datetime.utcnow()
            run.processing_time_seconds = round(time.perf_counter() - start_time, 3)
            try:
                await self._persist_run(run)
            except Exception:
                pass

            if job:
                job.status = JobStatus.STORAGE_LIMIT_REACHED if is_storage_limit else JobStatus.FAILED
                job.error = run.error_message
                job.completed_at = datetime.utcnow()
            raise

        return run, results, analytics

    async def run_from_dataset(
        self,
        dataset_id: str,
        organization_id: str = "org_default",
        idempotency_key: Optional[str] = None,
        triggered_by: Optional[str] = None,
        job: Optional[Any] = None,
    ) -> Tuple[ProcessingRun, List[ReconciliationResult], Dict[str, Any]]:
        """Fetch records from a validated dataset and execute the reconciliation pipeline."""
        from app.services.dataset_service import DatasetService

        dataset_svc = DatasetService(self._db)
        dataset = await dataset_svc.get_dataset(dataset_id, organization_id)
        if not dataset:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        raw_records = await dataset_svc.get_dataset_records(dataset_id)
        if not raw_records and dataset.raw_sample:
            raw_records = dataset.raw_sample

        # Apply mapping
        mapped_records = apply_column_mapping(raw_records, dataset.column_mapping)

        # Update dataset status
        dataset.processing_status = DatasetStatus.PROCESSING
        if self._db is not None:
            try:
                await self._db.datasets.update_one(
                    {"dataset_id": dataset_id},
                    {"$set": {"processing_status": DatasetStatus.PROCESSING.value}},
                )
            except Exception as exc:
                logger.warning("Failed to update dataset status to PROCESSING in DB: %s", exc)

        run, results, analytics = await self.run_from_data(
            txn_records=mapped_records,
            inv_records=[],
            bank_records=[],
            sett_records=[],
            dataset_name=dataset.filename,
            organization_id=organization_id,
            dataset_id=dataset_id,
            idempotency_key=idempotency_key,
            triggered_by=triggered_by,
            job=job,
        )

        # Update dataset completion
        if self._db is not None:
            try:
                new_status = (
                    DatasetStatus.COMPLETED.value
                    if run.status == RunStatus.COMPLETED
                    else DatasetStatus.VALIDATED.value
                )
                await self._db.datasets.update_one(
                    {"dataset_id": dataset_id},
                    {"$set": {
                        "processing_status": new_status,
                        "processing_run_id": run.run_id,
                    }},
                )
            except Exception as exc:
                logger.warning("Failed to update dataset status in DB: %s", exc)

        return run, results, analytics

    async def run_from_datasets(
        self,
        source_dataset_id: str,
        counterpart_dataset_id: str,
        organization_id: str = "org_default",
        idempotency_key: Optional[str] = None,
        triggered_by: Optional[str] = None,
        job: Optional[Any] = None,
    ) -> Tuple[ProcessingRun, List[ReconciliationResult], Dict[str, Any]]:
        """Cross-source reconciliation between two uploaded datasets.

        Generic: supports INVOICE ↔ BANK ↔ PAYMENT ↔ SETTLEMENT ↔ LEDGER ↔ GENERIC
        without requiring identical source-specific IDs.
        """
        from app.services.dataset_service import DatasetService
        from app.services.data_engine.column_mapper import apply_column_mapping
        from app.services.data_engine.canonical import normalize_to_canonical
        from app.services.finance_engine.canonical_reconciliation import reconcile_canonical_batch
        from app.models.dataset import get_compatible_types

        # 1. Tenant isolation & validation
        if source_dataset_id == counterpart_dataset_id:
            raise ValueError("Source and counterpart dataset cannot be the same.")

        dataset_svc = DatasetService(self._db)
        source_ds = await dataset_svc.get_dataset(source_dataset_id, organization_id)
        counterpart_ds = await dataset_svc.get_dataset(counterpart_dataset_id, organization_id)

        if not source_ds:
            raise ValueError(f"Source dataset '{source_dataset_id}' not found in organization '{organization_id}'.")
        if not counterpart_ds:
            raise ValueError(f"Counterpart dataset '{counterpart_dataset_id}' not found in organization '{organization_id}'.")

        # Auto-validate if UPLOADED (user clicked Reconcile without explicit Validate step)
        for ds in (source_ds, counterpart_ds):
            if ds.processing_status == DatasetStatus.UPLOADED:
                logger.info("Auto-validating UPLOADED dataset %s [%s] before reconciliation", ds.dataset_id, ds.dataset_type)
                try:
                    await dataset_svc.validate_dataset(ds.dataset_id, organization_id)
                    # Refresh
                    refreshed = await dataset_svc.get_dataset(ds.dataset_id, organization_id)
                    if refreshed:
                        if ds.dataset_id == source_dataset_id:
                            source_ds = refreshed
                        else:
                            counterpart_ds = refreshed
                except Exception as exc:
                    logger.warning("Auto-validation failed for %s: %s", ds.dataset_id, exc)

        # Validate status - allow UPLOADED that was just validated, but reject FAILED
        if source_ds.processing_status not in (DatasetStatus.VALIDATED, DatasetStatus.READY_FOR_RECONCILIATION, DatasetStatus.COMPLETED, DatasetStatus.UPLOADED):
            raise ValueError(f"Source dataset '{source_dataset_id}' is not ready (status={source_ds.processing_status}).")
        if counterpart_ds.processing_status not in (DatasetStatus.VALIDATED, DatasetStatus.READY_FOR_RECONCILIATION, DatasetStatus.COMPLETED, DatasetStatus.UPLOADED):
            raise ValueError(f"Counterpart dataset '{counterpart_dataset_id}' is not ready (status={counterpart_ds.processing_status}).")
        # If still UPLOADED after auto-validate attempt and valid_count==0, treat as not ready
        if source_ds.valid_count == 0 and source_ds.processing_status == DatasetStatus.UPLOADED:
            # Try one more validate
            try:
                await dataset_svc.validate_dataset(source_dataset_id, organization_id)
                source_ds = await dataset_svc.get_dataset(source_dataset_id, organization_id)
            except Exception:
                pass
        if counterpart_ds.valid_count == 0 and counterpart_ds.processing_status == DatasetStatus.UPLOADED:
            try:
                await dataset_svc.validate_dataset(counterpart_dataset_id, organization_id)
                counterpart_ds = await dataset_svc.get_dataset(counterpart_dataset_id, organization_id)
            except Exception:
                pass

        # Compatibility check
        compatible = get_compatible_types(source_ds.dataset_type)
        if counterpart_ds.dataset_type not in compatible:
            logger.warning("Dataset types %s and %s may have limited compatibility, proceeding anyway", source_ds.dataset_type, counterpart_ds.dataset_type)

        # 2. Idempotency / active run check (key includes both ids)
        combined_key = f"{source_dataset_id}:{counterpart_dataset_id}:{idempotency_key}" if idempotency_key else None
        if combined_key:
            existing = await self._check_idempotency(combined_key, organization_id)
            if existing:
                logger.info("Idempotent run_from_datasets returning existing %s", existing.run_id)
                results = await self.get_results_for_run(existing.run_id, organization_id)
                analytics = compute_run_analytics(results, existing)
                return existing, results, analytics

        # 3. Load records
        source_raw = await dataset_svc.get_dataset_records(source_dataset_id)
        counterpart_raw = await dataset_svc.get_dataset_records(counterpart_dataset_id)
        # Fallback to raw_sample if records not yet persisted
        if not source_raw and source_ds.raw_sample:
            source_raw = source_ds.raw_sample
        if not counterpart_raw and counterpart_ds.raw_sample:
            counterpart_raw = counterpart_ds.raw_sample

        if not source_raw:
            raise ValueError(f"Source dataset '{source_dataset_id}' has no records.")
        if not counterpart_raw:
            raise ValueError(f"Counterpart dataset '{counterpart_dataset_id}' has no records.")

        # 4. Apply column mappings
        source_mapped = apply_column_mapping(source_raw, source_ds.column_mapping)
        counterpart_mapped = apply_column_mapping(counterpart_raw, counterpart_ds.column_mapping)

        # 5. Normalize to canonical
        source_canonical = normalize_to_canonical(source_mapped, source_ds.dataset_type, organization_id, source_dataset_id)
        counterpart_canonical = normalize_to_canonical(counterpart_mapped, counterpart_ds.dataset_type, organization_id, counterpart_dataset_id)

        if not source_canonical:
            raise ValueError(f"Source dataset '{source_dataset_id}' has no canonical records after normalization.")
        if not counterpart_canonical:
            raise ValueError(f"Counterpart dataset '{counterpart_dataset_id}' has no canonical records.")

        # 6. Create run
        run = ProcessingRun(
            run_id=f"RUN-{uuid.uuid4().hex[:12].upper()}",
            organization_id=organization_id,
            dataset_id=source_dataset_id,
            source_dataset_id=source_dataset_id,
            counterpart_dataset_id=counterpart_dataset_id,
            source_type=source_ds.dataset_type,
            counterpart_type=counterpart_ds.dataset_type,
            dataset_name=f"{source_ds.filename} ↔ {counterpart_ds.filename}",
            dataset_source="dataset_pair",
            idempotency_key=combined_key,
            triggered_by=triggered_by,
            records_total=len(source_canonical),
            status=RunStatus.STARTED,
        )
        start_time = time.perf_counter()
        if job:
            job.records_total = len(source_canonical)
            job.progress_percent = 5.0

        await self._persist_run(run)
        await self._audit.log(
            AuditEventType.PROCESSING_STARTED,
            organization_id=organization_id,
            processing_run_id=run.run_id,
            actor=triggered_by or "system",
            message=f"Cross-source reconciliation started: {source_ds.dataset_type} ({len(source_canonical)}) ↔ {counterpart_ds.dataset_type} ({len(counterpart_canonical)})",
            metadata={"source_dataset_id": source_dataset_id, "counterpart_dataset_id": counterpart_dataset_id},
        )

        try:
            # 7. Update datasets to PROCESSING
            for ds_id in (source_dataset_id, counterpart_dataset_id):
                if self._db is not None:
                    try:
                        await self._db.datasets.update_one({"dataset_id": ds_id}, {"$set": {"processing_status": DatasetStatus.PROCESSING.value}})
                    except Exception:
                        pass

            run.status = RunStatus.PROCESSING
            await self._persist_run(run)

            # 8. Reconcile in bounded batches
            batch_size = max(100, getattr(settings, "reconciliation_batch_size", 1000))
            all_results: List[ReconciliationResult] = []
            processed = 0
            total = len(source_canonical)

            # For large counterpart, keep it indexed once
            for i in range(0, total, batch_size):
                chunk = source_canonical[i:i+batch_size]
                # For chunk, reconcile against full counterpart but with counterpart-only handling disabled per chunk
                # We call reconcile without counterpart-only for chunks, then add counterpart-only once at end
                chunk_results = reconcile_canonical_batch(
                    source_records=chunk,
                    counterpart_records=counterpart_canonical,
                    processing_run_id=run.run_id,
                    organization_id=organization_id,
                    source_dataset_id=source_dataset_id,
                    counterpart_dataset_id=counterpart_dataset_id,
                    source_type=source_ds.dataset_type,
                    counterpart_type=counterpart_ds.dataset_type,
                )
                # Filter out the counterpart-only MISSING results that are added per chunk (they have dataset_id == counterpart)
                # Keep only source-side results for batched processing; counterpart-only will be added once after loop
                source_results = [r for r in chunk_results if r.dataset_id != counterpart_dataset_id]
                # Also need to handle that reconcile_canonical_batch currently adds counterpart-only; we defer
                # So we re-run without counterpart-only: we already filtered

                for r in source_results:
                    r.organization_id = organization_id

                # Create exceptions and persist incrementally
                await self._create_exceptions(source_results, run.run_id, organization_id)
                await self._persist_results(source_results)
                all_results.extend(source_results)
                processed += len(chunk)

                elapsed_now = time.perf_counter() - start_time
                run.records_processed = processed
                run.progress_percent = round((processed / max(1, total)) * 100, 1)
                run.elapsed_seconds = round(elapsed_now, 2)
                run.processing_rate = round(processed / max(0.001, elapsed_now), 1)
                if job:
                    job.records_total = total
                    job.records_processed = processed
                    job.progress_percent = run.progress_percent
                    job.matched_records = sum(1 for r in all_results if r.status == ReconciliationStatus.MATCHED)
                    job.unmatched_records = sum(1 for r in all_results if r.status != ReconciliationStatus.MATCHED)
                    job.exception_count = job.unmatched_records
                    job.processing_rate = run.processing_rate
                    job.elapsed_seconds = run.elapsed_seconds
                if i % (batch_size * 2) == 0:
                    await self._persist_run(run)

            # Now handle counterpart-only records that never matched any source
            # Build set of matched counterpart ids from all_results
            matched_c_ids = set()
            for r in all_results:
                if r.bank_transaction_id:
                    matched_c_ids.add(r.bank_transaction_id)
                if r.invoice_id:
                    matched_c_ids.add(r.invoice_id)
                # Generic
                if r.transaction_id and r.transaction_id not in [s.get("record_id") for s in source_canonical]:
                    # This is a bit heuristic; rely on reconcile_canonical_batch's matched set
                    pass

            # Use the full reconcile to get counterpart-only, but dedupe
            full_results = reconcile_canonical_batch(
                source_records=source_canonical,
                counterpart_records=counterpart_canonical,
                processing_run_id=run.run_id,
                organization_id=organization_id,
                source_dataset_id=source_dataset_id,
                counterpart_dataset_id=counterpart_dataset_id,
            )
            # Extract counterpart-only (MISSING status with dataset_id == counterpart)
            counterpart_only = [r for r in full_results if r.status == ReconciliationStatus.MISSING and r.dataset_id == counterpart_dataset_id]
            # Avoid duplicates already counted
            existing_ids = {r.transaction_id for r in all_results}
            new_counterpart = [r for r in counterpart_only if r.transaction_id not in existing_ids]
            if new_counterpart:
                for r in new_counterpart:
                    r.organization_id = organization_id
                await self._create_exceptions(new_counterpart, run.run_id, organization_id)
                await self._persist_results(new_counterpart)
                all_results.extend(new_counterpart)

            results = all_results
            elapsed = time.perf_counter() - start_time
            run.processing_time_seconds = round(elapsed, 3)
            run.elapsed_seconds = run.processing_time_seconds
            run.records_processed = len(results)
            run.progress_percent = 100.0
            run.processing_rate = round(len(results) / max(0.001, elapsed), 1)
            run.records_received = total
            run.records_valid = total
            run.records_matched = sum(1 for r in results if r.status == ReconciliationStatus.MATCHED)
            run.records_ai_reviewed = sum(1 for r in results if r.status == ReconciliationStatus.AI_REVIEW)
            run.records_manual_review = sum(1 for r in results if r.status == ReconciliationStatus.MANUAL_REVIEW)
            run.records_mismatch = sum(1 for r in results if r.status == ReconciliationStatus.MISMATCH)
            run.records_duplicate = sum(1 for r in results if r.status == ReconciliationStatus.DUPLICATE)
            run.records_missing = sum(1 for r in results if r.status == ReconciliationStatus.MISSING)
            run.records_unmatched = len(results) - run.records_matched
            run.exceptions_created = run.records_manual_review + run.records_ai_reviewed + run.records_mismatch + run.records_missing
            run.match_rate = round(run.records_matched / len(results), 4) if results else 0.0
            run.average_confidence = round(sum(r.confidence for r in results) / len(results), 4) if results else 0.0
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()

            analytics = compute_run_analytics(results, run)
            await self._persist_run(run)

            # Update datasets to COMPLETED
            for ds_id in (source_dataset_id, counterpart_dataset_id):
                if self._db is not None:
                    try:
                        await self._db.datasets.update_one({"dataset_id": ds_id}, {"$set": {"processing_status": DatasetStatus.COMPLETED.value, "processing_run_id": run.run_id}})
                    except Exception:
                        pass

            await self._audit.log(
                AuditEventType.PROCESSING_COMPLETED,
                organization_id=organization_id,
                processing_run_id=run.run_id,
                message=f"Cross-source reconciliation completed: {run.records_matched} matched, {run.exceptions_created} exceptions in {elapsed:.2f}s",
                metadata={"match_rate": run.match_rate, "source": source_dataset_id, "counterpart": counterpart_dataset_id},
            )
            if job:
                job.status = JobStatus.COMPLETED
                job.progress_percent = 100.0
                job.records_processed = len(results)
                job.matched_records = run.records_matched
                job.unmatched_records = run.records_unmatched
                job.result = {"run_id": run.run_id, "status": RunStatus.COMPLETED.value, "records_processed": len(results), "records_matched": run.records_matched, "match_rate": run.match_rate, "analytics": analytics}

        except Exception as exc:
            err_str = str(exc)
            is_storage = "over your space quota" in err_str or "AtlasError" in err_str
            run.status = RunStatus.STORAGE_LIMIT_REACHED if is_storage else RunStatus.FAILED
            run.error_message = err_str
            run.completed_at = datetime.utcnow()
            run.processing_time_seconds = round(time.perf_counter() - start_time, 3)
            try:
                await self._persist_run(run)
            except Exception:
                pass
            if job:
                job.status = JobStatus.STORAGE_LIMIT_REACHED if is_storage else JobStatus.FAILED
                job.error = run.error_message
            raise

        return run, results, analytics

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    async def _check_idempotency(self, idempotency_key: str, organization_id: str) -> Optional[ProcessingRun]:
        if self._db is not None:
            doc = await self._db.processing_runs.find_one({
                "idempotency_key": idempotency_key,
                "organization_id": organization_id,
                "status": RunStatus.COMPLETED.value,
            })
            if doc:
                doc.pop("_id", None)
                return ProcessingRun(**doc)
            return None
        for r in memory_runs.values():
            if r.get("idempotency_key") == idempotency_key and r.get("organization_id") == organization_id:
                d = r.copy()
                d.pop("_id", None)
                return ProcessingRun(**d)
        return None

    async def _check_active_run(self, dataset_id: str, organization_id: str) -> Optional[ProcessingRun]:
        """Check if a reconciliation run is currently active for this dataset to prevent duplicate concurrent runs."""
        active_statuses = [RunStatus.QUEUED.value, RunStatus.STARTED.value, RunStatus.PROCESSING.value]
        if self._db is not None:
            try:
                doc = await self._db.processing_runs.find_one({
                    "dataset_id": dataset_id,
                    "organization_id": organization_id,
                    "status": {"$in": active_statuses},
                })
                if doc:
                    doc.pop("_id", None)
                    return ProcessingRun(**doc)
            except Exception as exc:
                logger.warning("Active run DB query failed: %s", exc)

        for r in memory_runs.values():
            if (
                r.get("dataset_id") == dataset_id
                and r.get("organization_id") == organization_id
                and r.get("status") in active_statuses
            ):
                d = r.copy()
                d.pop("_id", None)
                return ProcessingRun(**d)
        return None

    async def _run_ai_investigations(
        self,
        results: List[ReconciliationResult],
        transactions: dict,
        invoices: dict,
        bank_txns: dict,
        settlements: dict,
        processing_run_id: str,
        organization_id: str,
    ) -> List[ReconciliationResult]:
        """Run AI investigation for AI_REVIEW results with concurrency semaphore and batching."""
        ai_needed = [r for r in results if r.status == ReconciliationStatus.AI_REVIEW]
        logger.info("AI investigations needed: %d", len(ai_needed))

        if not ai_needed:
            return results

        # Sample up to top 25 representative cases for immediate pipeline investigation
        # so large dataset reconciliations finish in seconds rather than minutes.
        investigate_batch = ai_needed[:25]
        semaphore = asyncio.Semaphore(10)

        async def _investigate_one(result: ReconciliationResult) -> None:
            async with semaphore:
                txn = transactions.get(result.transaction_id)
                if not txn:
                    return

                exception_id = f"EX-{uuid.uuid4().hex.upper()}"

                investigation = await investigate_transaction(
                    txn=txn,
                    reconciliation_result=result,
                    exception_id=exception_id,
                    processing_run_id=processing_run_id,
                    invoice=invoices.get(result.invoice_id),
                    bank_txn=bank_txns.get(result.bank_transaction_id),
                    settlement=settlements.get(txn.transaction_id),
                )
                investigation.organization_id = organization_id

                # Update result with AI findings
                result.ai_investigated = True
                result.ai_confidence = investigation.confidence
                result.ai_finding = investigation.finding
                result.ai_recommendation = investigation.recommendation

                if (
                    investigation.recommendation == "RECONCILE"
                    and investigation.confidence >= 0.80
                    and not investigation.requires_manual_review
                ):
                    if result.confidence >= 0.60:
                        result.status = ReconciliationStatus.MATCHED
                        result.decision_source = "AI_ASSISTED"
                        result.reason = (
                            f"AI recommended reconciliation (confidence {investigation.confidence:.0%}). "
                            f"Finding: {investigation.finding}"
                        )
                    else:
                        result.status = ReconciliationStatus.MANUAL_REVIEW
                        result.decision_source = "AI_ASSISTED"
                        result.reason = (
                            f"AI found likely explanation ({investigation.finding}) but "
                            f"finance confidence ({result.confidence:.0%}) is too low for auto-reconciliation."
                        )
                elif investigation.recommendation == "REJECT":
                    result.status = ReconciliationStatus.MISMATCH
                    result.decision_source = "AI_ASSISTED"
                    result.reason = f"AI investigation: {investigation.finding}"

        await asyncio.gather(*[_investigate_one(r) for r in investigate_batch])

        if investigate_batch:
            await self._audit.log(
                AuditEventType.AI_INVESTIGATION_COMPLETED,
                organization_id=organization_id,
                entity_type="run",
                entity_id=processing_run_id,
                processing_run_id=processing_run_id,
                message=f"Completed {len(investigate_batch)} AI investigations for run {processing_run_id}",
                metadata={"investigated_count": len(investigate_batch)},
            )

        return results

    async def _create_exceptions(
        self,
        results: List[ReconciliationResult],
        run_id: str,
        organization_id: str,
    ) -> None:
        """Create exceptions for non-matched results in bulk."""
        created = await self._exceptions.create_many_from_results(results, run_id, organization_id)
        if created:
            await self._audit.log(
                AuditEventType.EXCEPTION_CREATED,
                organization_id=organization_id,
                entity_type="run",
                entity_id=run_id,
                processing_run_id=run_id,
                message=f"Created {len(created)} exceptions for processing run {run_id}.",
                metadata={"count": len(created)},
            )

    async def _persist_results(self, results: List[ReconciliationResult]) -> None:
        """Persist reconciliation results in batches of 2000 documents."""
        if not results:
            return

        docs = [dict_to_mongo(r) for r in results]
        run_id = results[0].processing_run_id
        memory_results[run_id] = docs

        if self._db is not None:
            try:
                batch_size = 2000
                for i in range(0, len(docs), batch_size):
                    chunk = docs[i:i + batch_size]
                    await self._db.reconciliation_results.insert_many(chunk, ordered=False)
            except Exception as exc:
                logger.error("Failed to persist results batch: %s", exc)

    async def _persist_run(self, run: ProcessingRun) -> None:
        """Upsert a processing run."""
        memory_runs[run.run_id] = dict_to_mongo(run)
        if self._db is not None:
            try:
                await self._db.processing_runs.replace_one(
                    {"run_id": run.run_id},
                    dict_to_mongo(run),
                    upsert=True,
                )
            except Exception as exc:
                logger.error("Failed to persist run: %s", exc)

    async def get_results_for_run(self, run_id: str, organization_id: str) -> List[ReconciliationResult]:
        if self._db is not None:
            cursor = self._db.reconciliation_results.find({"processing_run_id": run_id, "organization_id": organization_id})
            docs = await cursor.to_list(length=10000)
            results = []
            for d in docs:
                d.pop("_id", None)
                results.append(ReconciliationResult(**d))
            return results
        if run_id in memory_results:
            return [ReconciliationResult(**d.copy()) for d in memory_results[run_id]]
        return []
