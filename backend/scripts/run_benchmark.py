"""Finova — Benchmark Script.

Processes 250+ records and reports performance metrics.
"""
import sys
import os
import asyncio
import time

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.data_generator import generate_dataset, dataset_to_dicts
from app.services.data_engine.ingestion import ingest_from_dict_list
from app.services.data_engine.cleaner import clean_transactions, clean_invoices, clean_bank_transactions, clean_settlements
from app.services.data_engine.normalizer import normalize_transactions, normalize_invoices, normalize_bank_transactions, normalize_settlements
from app.services.data_engine.validator import validate_transactions
from app.services.finance_engine.duplicate_detector import detect_duplicates
from app.services.finance_engine.reconciliation import reconcile_batch
from app.services.analytics_engine import compute_run_analytics
from app.models.processing_run import ProcessingRun, RunStatus
from app.models.reconciliation import ReconciliationStatus


async def run_benchmark(num_records: int = 250, seed: int = 42):
    print("\n" + "=" * 60)
    print("  FINOVA BENCHMARK")
    print("=" * 60)
    print(f"  Records:  {num_records}")
    print(f"  Seed:     {seed}")
    print("=" * 60)

    start = time.perf_counter()

    # Generate data
    print("\n[1] Generating synthetic dataset...")
    txns, invs, banks, settlements = generate_dataset(num_records=num_records, seed=seed)
    data = dataset_to_dicts(txns, invs, banks, settlements)

    # Clean
    print("[2] Cleaning...")
    txn_cleaned = clean_transactions(data["transactions"])
    inv_cleaned = clean_invoices(data["invoices"])
    bank_cleaned = clean_bank_transactions(data["bank_transactions"])
    sett_cleaned = clean_settlements(data["settlements"])

    # Normalize
    print("[3] Normalizing...")
    run_id = "BENCHMARK-001"
    transactions, _ = normalize_transactions(txn_cleaned.records, run_id)
    invoices, _ = normalize_invoices(inv_cleaned.records, run_id)
    bank_txns, _ = normalize_bank_transactions(bank_cleaned.records, run_id)
    sett_objs, _ = normalize_settlements(sett_cleaned.records, run_id)

    # Validate
    print("[4] Validating...")
    valid_txns, report = validate_transactions(transactions)

    # Duplicate detection
    print("[5] Detecting duplicates...")
    unique_txns, duplicate_ids = detect_duplicates(valid_txns)

    # Reconciliation
    print("[6] Running reconciliation engine...")
    results = reconcile_batch(
        transactions=unique_txns,
        invoices=invoices,
        bank_transactions=bank_txns,
        settlements=sett_objs,
        processing_run_id=run_id,
        duplicate_ids=duplicate_ids,
    )

    # Add duplicate results
    for txn in valid_txns:
        if txn.transaction_id in duplicate_ids:
            from app.models.reconciliation import ReconciliationResult, ConfidenceSignals
            results.append(ReconciliationResult(
                processing_run_id=run_id,
                transaction_id=txn.transaction_id,
                customer_id=txn.customer_id,
                status=ReconciliationStatus.DUPLICATE,
                confidence=0.95,
                reason="Duplicate detected.",
                ground_truth_status=txn.ground_truth_status,
            ))

    elapsed = time.perf_counter() - start

    # Build processing run for analytics
    run = ProcessingRun(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        dataset_source="synthetic",
        records_received=num_records,
        records_valid=report.records_valid,
        records_invalid=report.records_invalid,
        records_matched=sum(1 for r in results if r.status == ReconciliationStatus.MATCHED),
        records_ai_reviewed=0,
        records_manual_review=sum(1 for r in results if r.status == ReconciliationStatus.MANUAL_REVIEW),
        records_duplicate=sum(1 for r in results if r.status == ReconciliationStatus.DUPLICATE),
        processing_time_seconds=elapsed,
    )

    analytics = compute_run_analytics(results, run)

    # Print report
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    total = len(results)
    matched = analytics["matched_records"]
    ai_reviewed = analytics["ai_review_count"]
    manual = analytics["manual_review_count"]
    duplicates = analytics.get("duplicate_count", 0)
    exceptions = analytics["exception_count"]

    print(f"  Records processed:      {total}")
    print(f"  Matched (auto):         {matched}")
    print(f"  AI review:              {ai_reviewed}")
    print(f"  Manual review:          {manual}")
    print(f"  Duplicates:             {duplicates}")
    print(f"  Exceptions:             {exceptions}")
    print()
    print(f"  Match rate:             {analytics['match_rate']*100:.2f}%")
    print(f"  Average confidence:     {analytics['average_confidence']*100:.2f}%")
    print(f"  Processing time:        {elapsed:.3f}s")
    print()

    if analytics.get("ground_truth_available"):
        print(f"  Precision:              {analytics['precision']*100:.2f}%")
        print(f"  Recall:                 {analytics['recall']*100:.2f}%")
        print(f"  F1 Score:               {analytics['f1_score']*100:.2f}%")
        print(f"  True Positives:         {analytics['true_positives']}")
        print(f"  False Positives:        {analytics['false_positives']}")
        print(f"  False Negatives:        {analytics['false_negatives']}")

    print("=" * 60)
    print("  BENCHMARK COMPLETE")
    print("=" * 60)
    return analytics


if __name__ == "__main__":
    records = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    asyncio.run(run_benchmark(records, seed))
