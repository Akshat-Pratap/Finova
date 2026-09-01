"""Finova — Financial Analytics Engine.

Computes real, organization-scoped reconciliation KPIs, financial metrics,
classification metrics, and historical reconciliation trends from persisted records.
Never fabricates metrics.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.models.processing_run import ProcessingRun
from app.models.reconciliation import ReconciliationResult, ReconciliationStatus
from app.services.memory_store import memory_runs

logger = logging.getLogger(__name__)


def compute_run_analytics(
    results: List[ReconciliationResult],
    run: ProcessingRun,
) -> Dict[str, Any]:
    """Compute analytics for a single processing run."""
    total = len(results)
    if total == 0:
        return _empty_analytics(run)

    matched = sum(1 for r in results if r.status == ReconciliationStatus.MATCHED)
    ai_review = sum(1 for r in results if r.status == ReconciliationStatus.AI_REVIEW or r.ai_investigated)
    manual_review = sum(1 for r in results if r.status == ReconciliationStatus.MANUAL_REVIEW)
    mismatch = sum(1 for r in results if r.status == ReconciliationStatus.MISMATCH)
    duplicate = sum(1 for r in results if r.status == ReconciliationStatus.DUPLICATE)
    missing = sum(1 for r in results if r.status == ReconciliationStatus.MISSING)
    exceptions = total - matched

    match_rate = matched / total if total > 0 else 0.0
    avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0.0

    # High/medium/low confidence split
    high_confidence = sum(1 for r in results if r.confidence >= 0.90)
    medium_confidence = sum(1 for r in results if 0.70 <= r.confidence < 0.90)
    low_confidence = sum(1 for r in results if r.confidence < 0.70)

    # Monetary values
    total_volume = sum((r.actual_amount or r.expected_amount or Decimal("0")) for r in results)
    reconciled_val = sum((r.actual_amount or r.expected_amount or Decimal("0")) for r in results if r.status == ReconciliationStatus.MATCHED)
    unreconciled_val = total_volume - reconciled_val

    analytics: Dict[str, Any] = {
        "total_records": total,
        "matched_records": matched,
        "ai_review_count": ai_review,
        "manual_review_count": manual_review,
        "mismatch_count": mismatch,
        "duplicate_count": duplicate,
        "missing_count": missing,
        "exception_count": exceptions,
        "match_rate": round(match_rate, 4),
        "average_confidence": round(avg_confidence, 4),
        "high_confidence_count": high_confidence,
        "medium_confidence_count": medium_confidence,
        "low_confidence_count": low_confidence,
        "gross_transaction_volume": float(total_volume),
        "reconciled_value": float(reconciled_val),
        "unreconciled_value": float(unreconciled_val),
        "processing_time_seconds": run.processing_time_seconds,
        "run_id": run.run_id,
        "dataset_source": run.dataset_source,
    }

    # Classification metrics (only when ground truth available)
    ground_truth_results = [r for r in results if r.ground_truth_status is not None]
    if ground_truth_results:
        metrics = _compute_classification_metrics(ground_truth_results)
        analytics.update(metrics)
        analytics["ground_truth_available"] = True
    else:
        analytics["ground_truth_available"] = False

    return analytics


def _compute_classification_metrics(results: List[ReconciliationResult]) -> Dict[str, Any]:
    """Compute precision, recall, F1 against ground truth."""
    tp = 0
    fp = 0
    tn = 0
    fn = 0

    for r in results:
        predicted_positive = r.status == ReconciliationStatus.MATCHED
        truth_positive = r.ground_truth_status in ("MATCH",)

        if predicted_positive and truth_positive:
            tp += 1
        elif predicted_positive and not truth_positive:
            fp += 1
        elif not predicted_positive and not truth_positive:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
    }


def _empty_analytics(run: ProcessingRun) -> Dict[str, Any]:
    return {
        "total_records": 0,
        "matched_records": 0,
        "ai_review_count": 0,
        "manual_review_count": 0,
        "exception_count": 0,
        "match_rate": 0.0,
        "average_confidence": 0.0,
        "gross_transaction_volume": 0.0,
        "reconciled_value": 0.0,
        "unreconciled_value": 0.0,
        "processing_time_seconds": 0.0,
        "run_id": run.run_id,
        "ground_truth_available": False,
    }


async def get_summary_analytics(db, organization_id: Optional[str] = None) -> Dict[str, Any]:
    """Get aggregate analytics across all processing runs for an organization."""
    match_query: Dict[str, Any] = {}
    if organization_id and organization_id != "org_default":
        match_query["organization_id"] = organization_id

    if db is not None:
        try:
            pipeline = [
                {"$match": match_query} if match_query else {"$match": {}},
                {
                    "$group": {
                        "_id": None,
                        "total_runs": {"$sum": 1},
                        "total_records": {"$sum": "$records_processed"},
                        "total_matched": {"$sum": "$records_matched"},
                        "total_ai_reviewed": {"$sum": "$records_ai_reviewed"},
                        "total_manual_review": {"$sum": "$records_manual_review"},
                        "total_duplicates": {"$sum": "$records_duplicate"},
                        "avg_match_rate": {"$avg": "$match_rate"},
                        "avg_confidence": {"$avg": "$average_confidence"},
                        "total_exceptions": {"$sum": "$exceptions_created"},
                    }
                }
            ]
            cursor = db.processing_runs.aggregate(pipeline)
            docs = await cursor.to_list(length=1)
            summary = docs[0] if docs else {}
            summary.pop("_id", None)

            # Get historical trend points
            trend_cursor = db.processing_runs.find(match_query).sort("started_at", 1).limit(14)
            trend_docs = await trend_cursor.to_list(length=14)
            trends = [
                {
                    "run_id": t.get("run_id"),
                    "date": t.get("started_at", "").strftime("%b %d") if hasattr(t.get("started_at"), "strftime") else str(t.get("started_at", ""))[:10],
                    "matched": t.get("records_matched", 0),
                    "exceptions": t.get("exceptions_created", 0),
                    "match_rate": round(t.get("match_rate", 0) * 100, 1),
                }
                for t in trend_docs
            ]

            summary["trends"] = trends
            summary["total_runs"] = summary.get("total_runs", 0)
            summary["total_records"] = summary.get("total_records", 0)
            summary["total_matched"] = summary.get("total_matched", 0)
            summary["avg_match_rate"] = round(summary.get("avg_match_rate", 0) or 0, 4)
            summary["avg_confidence"] = round(summary.get("avg_confidence", 0) or 0, 4)
            summary["total_exceptions"] = summary.get("total_exceptions", 0)
            return summary

        except Exception as exc:
            logger.error("Failed to get aggregate summary analytics: %s", exc)

    # In-memory aggregation fallback
    runs = [r for r in memory_runs.values() if not organization_id or organization_id == "org_default" or r.get("organization_id") == organization_id]
    if not runs:
        return _empty_summary()

    total_runs = len(runs)
    total_records = sum(r.get("records_processed", 0) for r in runs)
    total_matched = sum(r.get("records_matched", 0) for r in runs)
    total_exceptions = sum(r.get("exceptions_created", 0) for r in runs)
    avg_match_rate = sum(r.get("match_rate", 0) for r in runs) / total_runs if total_runs else 0.0
    avg_conf = sum(r.get("average_confidence", 0) for r in runs) / total_runs if total_runs else 0.0

    trends = [
        {
            "run_id": r.get("run_id"),
            "date": str(r.get("started_at", ""))[:10],
            "matched": r.get("records_matched", 0),
            "exceptions": r.get("exceptions_created", 0),
            "match_rate": round(r.get("match_rate", 0) * 100, 1),
        }
        for r in sorted(runs, key=lambda x: str(x.get("started_at", "")))[-14:]
    ]

    return {
        "total_runs": total_runs,
        "total_records": total_records,
        "total_matched": total_matched,
        "avg_match_rate": round(avg_match_rate, 4),
        "avg_confidence": round(avg_conf, 4),
        "total_exceptions": total_exceptions,
        "trends": trends,
    }


def _empty_summary() -> Dict[str, Any]:
    return {
        "total_runs": 0,
        "total_records": 0,
        "total_matched": 0,
        "avg_match_rate": 0.0,
        "avg_confidence": 0.0,
        "total_exceptions": 0,
        "trends": [],
        "note": "No reconciliation runs recorded yet.",
    }
