"""Finova — Tests: AI Engine."""
import pytest
import asyncio
from decimal import Decimal

from app.services.ai_engine.fallback import FallbackAIProvider, _analyze_context
from app.services.ai_engine.schemas import AIInvestigationResponse


@pytest.fixture
def fee_context():
    return {
        "transaction": {"transaction_id": "TXN-001", "amount": "10000", "reference_id": "REF-001"},
        "invoice": {"invoice_id": "INV-001", "invoice_amount": "10000"},
        "bank_transaction": {"bank_transaction_id": "BNK-001", "amount": "9800", "reference": "REF-001"},
        "settlement": {
            "settlement_id": "SET-001",
            "gross_amount": "10000",
            "fees": "200",
            "tax": "36",
            "net_amount": "9764",
        },
        "confidence_signals": {"reference_match": True, "amount_match": False},
        "confidence_score": 0.72,
    }


@pytest.fixture
def missing_ref_context():
    return {
        "transaction": {"transaction_id": "TXN-002", "amount": "5000", "reference_id": None},
        "invoice": {},
        "bank_transaction": {},
        "settlement": {},
        "confidence_signals": {},
        "confidence_score": 0.30,
    }


def test_fallback_provider_available():
    provider = FallbackAIProvider()
    assert provider.is_available
    assert provider.provider_name == "DEMO MODE"


def test_fallback_fee_discrepancy(fee_context):
    response = _analyze_context(fee_context)
    assert isinstance(response, AIInvestigationResponse)
    assert "fee" in response.finding.lower() or "processing" in response.finding.lower()
    assert response.confidence > 0.70
    assert response.recommendation == "RECONCILE"
    assert not response.requires_manual_review


def test_fallback_missing_reference(missing_ref_context):
    response = _analyze_context(missing_ref_context)
    assert response.requires_manual_review
    assert response.recommendation == "MANUAL_REVIEW"


def test_fallback_returns_valid_schema(fee_context):
    response = _analyze_context(fee_context)
    assert 0.0 <= response.confidence <= 1.0
    assert response.recommendation in ("RECONCILE", "MANUAL_REVIEW", "REJECT")
    assert len(response.evidence) > 0


def test_ai_response_schema_validation():
    response = AIInvestigationResponse(
        finding="Test finding",
        reason="Test reason",
        confidence=0.85,
        recommendation="RECONCILE",
        requires_manual_review=False,
        evidence=["Evidence 1", "Evidence 2"],
    )
    assert response.confidence == 0.85
    assert response.recommendation == "RECONCILE"


def test_ai_response_invalid_recommendation():
    """Invalid recommendation should be normalized to MANUAL_REVIEW."""
    response = AIInvestigationResponse(
        finding="Test",
        reason="Test",
        confidence=0.5,
        recommendation="INVALID_RECOMMENDATION",
        requires_manual_review=True,
    )
    assert response.recommendation == "MANUAL_REVIEW"


def test_ai_response_empty_finding():
    """Empty finding should be replaced with default."""
    response = AIInvestigationResponse(
        finding="",
        reason="Test",
        confidence=0.5,
        recommendation="MANUAL_REVIEW",
    )
    assert response.finding == "Unable to determine"


@pytest.mark.asyncio
async def test_fallback_investigate_async(fee_context):
    provider = FallbackAIProvider()
    result = await provider.investigate(fee_context, "investigate this")
    assert "finding" in result
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
