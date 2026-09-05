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
            run_id=f"RUN-{uuid.uuid4().hex[:8].upper()}",
            organization_id=organization_id,
            dataset_source="synthetic",
            dataset_name=f"synthetic_{num_records}_{seed}",
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
            run.records_matched = sum(1 for r in results if r.status == ReconciliationStatus.MATCHED)
            run.records_ai_reviewed = sum(1 for r in results if r.ai_investigated)
            run.records_manual_review = sum(1 for r in results if r.status == ReconciliationStatus.MANUAL_REVIEW)
            run.records_mismatch = sum(1 for r in results if r.status == ReconciliationStatus.MISMATCH)
            run.records_duplicate = sum(1 for r in results if r.status == ReconciliationStatus.DUPLICATE)
            run.records_missing = sum(1 for r in results if r.status == ReconciliationStatus.MISSING)
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
        """Run reconciliation on uploaded or imported raw data."""
        # Idempotency check
        if idempotency_key:
            existing = await self._check_idempotency(idempotency_key, organization_id)
            if existing:
                logger.info("Idempotent request returning existing run: %s", existing.run_id)
                results = await self.get_results_for_run(existing.run_id, organization_id)
                analytics = compute_run_analytics(results, existing)
                return existing, results, analytics

        run = ProcessingRun(
            run_id=f"RUN-{uuid.uuid4().hex[:8].upper()}",
            organization_id=organization_id,
            dataset_id=dataset_id,
            dataset_source="uploaded" if not dataset_name.startswith("razorpay") else "razorpay",
            dataset_name=dataset_name,
            idempotency_key=idempotency_key,
            triggered_by=triggered_by,
        )
        start_time = time.perf_counter()

        if job:
            job.records_total = len(txn_records)
            job.progress_percent = 10.0

        await self._audit.log(
            AuditEventType.PROCESSING_STARTED,
            organization_id=organization_id,
            processing_run_id=run.run_id,
            actor=triggered_by or "system",
            actor_id=triggered_by,
            message=f"Processing {len(txn_records)} records for organization {organization_id}",
        )

        try:
            txn_cleaned = clean_transactions(txn_records)
            inv_cleaned = clean_invoices(inv_records)
            bank_cleaned = clean_bank_transactions(bank_records)
            sett_cleaned = clean_settlements(sett_records)

            run.records_received = len(txn_records)
            run.records_invalid = txn_cleaned.invalid_removed
            run.duplicates_input = txn_cleaned.duplicates_removed

            if job:
                job.progress_percent = 25.0

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

            if job:
                job.progress_percent = 45.0

            unique_txns, duplicate_ids = detect_duplicates(valid_txns)

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
                r.dataset_id = dataset_id

            for txn in valid_txns:
                if txn.transaction_id in duplicate_ids:
                    results.append(ReconciliationResult(
                        processing_run_id=run.run_id,
                        organization_id=organization_id,
                        dataset_id=dataset_id,
                        transaction_id=txn.transaction_id,
                        customer_id=txn.customer_id,
                        status=ReconciliationStatus.DUPLICATE,
                        confidence=0.95,
                        decision_source="AUTOMATED_RULE",
                        reason="Duplicate transaction detected.",
                    ))

            if job:
                job.progress_percent = 65.0

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

            if job:
                job.progress_percent = 85.0

            await self._create_exceptions(results, run.run_id, organization_id)
            await self._persist_results(results)

            elapsed = time.perf_counter() - start_time
            run.processing_time_seconds = round(elapsed, 3)
            run.records_matched = sum(1 for r in results if r.status == ReconciliationStatus.MATCHED)
            run.records_ai_reviewed = sum(1 for r in results if r.ai_investigated)
            run.records_manual_review = sum(1 for r in results if r.status == ReconciliationStatus.MANUAL_REVIEW)
            run.records_duplicate = sum(1 for r in results if r.status == ReconciliationStatus.DUPLICATE)
            run.records_mismatch = sum(1 for r in results if r.status == ReconciliationStatus.MISMATCH)
            run.records_missing = sum(1 for r in results if r.status == ReconciliationStatus.MISSING)
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
                job.progress_percent = 100.0
                job.records_processed = len(results)

        except Exception as exc:
            run.status = RunStatus.FAILED
            run.error_message = str(exc)
            run.completed_at = datetime.utcnow()
            await self._persist_run(run)
            logger.error("Reconciliation run failed: %s", exc, exc_info=True)
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
            await self._db.datasets.update_one(
                {"dataset_id": dataset_id},
                {"$set": {"processing_status": DatasetStatus.PROCESSING.value}},
            )

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
            await self._db.datasets.update_one(
                {"dataset_id": dataset_id},
                {"$set": {
                    "processing_status": DatasetStatus.COMPLETED.value,
                    "processing_run_id": run.run_id,
                }},
            )

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
        """Run AI investigation for all AI_REVIEW results with concurrency semaphore."""
        ai_needed = [r for r in results if r.status == ReconciliationStatus.AI_REVIEW]
        logger.info("AI investigations needed: %d", len(ai_needed))

        semaphore = asyncio.Semaphore(5)

        async def _investigate_one(result: ReconciliationResult) -> None:
            async with semaphore:
                txn = transactions.get(result.transaction_id)
                if not txn:
                    return

                exception_id = f"EX-{uuid.uuid4().hex[:8].upper()}"

                await self._audit.log(
                    AuditEventType.AI_INVESTIGATION_STARTED,
                    organization_id=organization_id,
                    entity_type="transaction",
                    entity_id=result.transaction_id,
                    processing_run_id=processing_run_id,
                    message=f"AI investigating transaction {result.transaction_id}",
                )

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

                await self._audit.log(
                    AuditEventType.AI_INVESTIGATION_COMPLETED,
                    organization_id=organization_id,
                    entity_type="transaction",
                    entity_id=result.transaction_id,
                    processing_run_id=processing_run_id,
                    message=f"AI finding: {investigation.finding} (confidence {investigation.confidence:.0%})",
                    metadata={"recommendation": investigation.recommendation},
                )

        if ai_needed:
            await asyncio.gather(*[_investigate_one(r) for r in ai_needed])
        return results

    async def _create_exceptions(
        self,
        results: List[ReconciliationResult],
        run_id: str,
        organization_id: str,
    ) -> None:
        """Create exceptions for non-matched results."""
        count = 0
        for result in results:
            if result.status != ReconciliationStatus.MATCHED:
                exc = await self._exceptions.create_from_result(result, run_id)
                if exc:
                    count += 1
                    exc.organization_id = organization_id
                    await self._audit.log(
                        AuditEventType.EXCEPTION_CREATED,
                        organization_id=organization_id,
                        entity_type="exception",
                        entity_id=exc.exception_id,
                        processing_run_id=run_id,
                        message=f"Exception {exc.exception_id}: {exc.type.value}",
                    )

    async def _persist_results(self, results: List[ReconciliationResult]) -> None:
        """Persist reconciliation results in batches of 500 documents."""
        if not results:
            return

        docs = [dict_to_mongo(r) for r in results]
        run_id = results[0].processing_run_id
        memory_results[run_id] = docs

        if self._db is not None:
            try:
                batch_size = 500
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
