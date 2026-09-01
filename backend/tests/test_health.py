"""Finova — Tests: Health."""
import pytest


def test_imports():
    """Verify all critical modules import correctly."""
    from app.core.config import settings
    from app.models.transaction import Transaction
    from app.models.invoice import Invoice
    from app.models.reconciliation import ReconciliationResult
    from app.services.data_generator import generate_dataset
    from app.services.finance_engine.confidence import compute_confidence
    from app.services.ai_engine.fallback import FallbackAIProvider
    assert settings.app_name == "Finova"


def test_settings():
    from app.core.config import settings
    assert 0 < settings.auto_reconcile_threshold < 1
    assert 0 < settings.ai_review_threshold < 1
    assert settings.auto_reconcile_threshold > settings.ai_review_threshold


def test_weight_configuration():
    from app.core.config import settings
    total = (
        settings.weight_reference +
        settings.weight_amount +
        settings.weight_customer +
        settings.weight_date +
        settings.weight_invoice +
        settings.weight_description
    )
    assert abs(total - 1.0) < 0.01, f"Weights must sum to 1.0, got {total}"
