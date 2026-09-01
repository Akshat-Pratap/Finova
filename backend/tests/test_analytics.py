"""Finova — Tests: Analytics Engine."""
import pytest
from decimal import Decimal
from datetime import datetime

from app.services.analytics_engine import compute_run_analytics, _compute_classification_metrics
from app.models.reconciliation import ReconciliationResult, ReconciliationStatus
from app.models.processing_run import ProcessingRun, RunStatus


def _make_run():
    return ProcessingRun(
        run_id="RUN-TEST",
        status=RunStatus.COMPLETED,
        dataset_source="synthetic",
        processing_time_seconds=1.5,
    )


def _make_result(status: ReconciliationStatus, confidence: float = 0.90, gt: str = None):
    return ReconciliationResult(
        processing_run_id="RUN-TEST",
        transaction_id=f"TXN-{hash(status.value + str(confidence))}",
        status=status,
        confidence=confidence,
        reason="test",
        ground_truth_status=gt,
    )


def test_analytics_empty():
    run = _make_run()
    analytics = compute_run_analytics([], run)
    assert analytics["total_records"] == 0
    assert analytics["match_rate"] == 0.0


def test_analytics_all_matched():
    results = [_make_result(ReconciliationStatus.MATCHED, 0.95) for _ in range(10)]
    run = _make_run()
    analytics = compute_run_analytics(results, run)
    assert analytics["total_records"] == 10
    assert analytics["matched_records"] == 10
    assert analytics["match_rate"] == 1.0


def test_analytics_mixed():
    results = [
        _make_result(ReconciliationStatus.MATCHED, 0.95),
        _make_result(ReconciliationStatus.MATCHED, 0.92),
        _make_result(ReconciliationStatus.AI_REVIEW, 0.75),
        _make_result(ReconciliationStatus.MANUAL_REVIEW, 0.50),
        _make_result(ReconciliationStatus.DUPLICATE, 0.95),
    ]
    run = _make_run()
    analytics = compute_run_analytics(results, run)
    assert analytics["total_records"] == 5
    assert analytics["matched_records"] == 2
    assert analytics["ai_review_count"] == 1
    assert analytics["manual_review_count"] == 1
    assert analytics["duplicate_count"] == 1
    assert analytics["match_rate"] == pytest.approx(0.40)


def test_classification_metrics():
    """Test precision/recall/F1 with known ground truth."""
    results = [
        # True positives (predicted MATCHED, truth MATCH)
        _make_result(ReconciliationStatus.MATCHED, 0.95, "MATCH"),
        _make_result(ReconciliationStatus.MATCHED, 0.92, "MATCH"),
        _make_result(ReconciliationStatus.MATCHED, 0.90, "MATCH"),
        # False positive (predicted MATCHED, truth is not MATCH)
        _make_result(ReconciliationStatus.MATCHED, 0.91, "MISMATCH"),
        # True negative (predicted non-MATCHED, truth not MATCH)
        _make_result(ReconciliationStatus.AI_REVIEW, 0.75, "MISMATCH"),
        # False negative (predicted non-MATCHED, truth MATCH)
        _make_result(ReconciliationStatus.AI_REVIEW, 0.72, "MATCH"),
    ]
    metrics = _compute_classification_metrics(results)
    assert metrics["true_positives"] == 3
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == pytest.approx(3/4, abs=0.01)
    assert metrics["recall"] == pytest.approx(3/4, abs=0.01)
    assert 0.0 <= metrics["f1_score"] <= 1.0


def test_average_confidence():
    results = [
        _make_result(ReconciliationStatus.MATCHED, 0.90),
        _make_result(ReconciliationStatus.MATCHED, 0.80),
    ]
    run = _make_run()
    analytics = compute_run_analytics(results, run)
    assert analytics["average_confidence"] == pytest.approx(0.85)
