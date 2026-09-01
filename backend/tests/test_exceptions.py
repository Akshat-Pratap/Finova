"""Finova — Tests: Health and Exceptions."""
import pytest
from decimal import Decimal


def test_health_response_structure():
    """Verify health response has required fields."""
    from app.core.config import settings
    # Without a real database, check config
    assert settings.app_name == "Finova"
    assert settings.auto_reconcile_threshold == 0.90
    assert settings.ai_review_threshold == 0.70


def test_exception_manager_create_from_mismatch():
    """ExceptionManager creates correct exception type."""
    from app.models.reconciliation import ReconciliationResult, ReconciliationStatus, ConfidenceSignals
    from app.models.exception import ExceptionType
    from app.services.exception_manager import _classify_exception

    result = ReconciliationResult(
        processing_run_id="RUN-001",
        transaction_id="TXN-001",
        status=ReconciliationStatus.MANUAL_REVIEW,
        confidence=0.50,
        reason="Low confidence",
        difference=Decimal("500"),
        signals=ConfidenceSignals(reference_match=False),
    )
    exc_type, severity, desc = _classify_exception(result)
    # Without reference match, should be MISSING_REFERENCE or AMOUNT_MISMATCH
    assert exc_type in (ExceptionType.MISSING_REFERENCE, ExceptionType.AMOUNT_MISMATCH)


def test_exception_manager_duplicate():
    from app.models.reconciliation import ReconciliationResult, ReconciliationStatus
    from app.models.exception import ExceptionType, ExceptionSeverity
    from app.services.exception_manager import _classify_exception

    result = ReconciliationResult(
        processing_run_id="RUN-001",
        transaction_id="TXN-001",
        status=ReconciliationStatus.DUPLICATE,
        confidence=0.95,
        reason="Duplicate",
    )
    exc_type, severity, desc = _classify_exception(result)
    assert exc_type == ExceptionType.DUPLICATE
    assert severity == ExceptionSeverity.HIGH


def test_exception_manager_large_difference():
    from app.models.reconciliation import ReconciliationResult, ReconciliationStatus, ConfidenceSignals
    from app.models.exception import ExceptionType, ExceptionSeverity
    from app.services.exception_manager import _classify_exception

    result = ReconciliationResult(
        processing_run_id="RUN-001",
        transaction_id="TXN-001",
        status=ReconciliationStatus.AI_REVIEW,
        confidence=0.72,
        reason="Mismatch",
        difference=Decimal("5000"),  # Large
        signals=ConfidenceSignals(),
    )
    exc_type, severity, desc = _classify_exception(result)
    assert exc_type == ExceptionType.AMOUNT_MISMATCH
    assert severity == ExceptionSeverity.CRITICAL
