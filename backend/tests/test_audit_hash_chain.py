"""Finova — Audit Log SHA-256 Hash Chain Integrity Tests."""
from __future__ import annotations

import pytest
from app.models.audit_log import AuditEventType
from app.services.audit_logger import AuditLogger, _scrub_sensitive


def test_sensitive_data_scrubbing():
    dirty_meta = {
        "user_email": "finance@finova.ai",
        "api_key": "rzp_live_secret_998877",
        "nested": {"password": "SuperSecretPassword123!", "amount": 5000},
    }
    cleaned = _scrub_sensitive(dirty_meta)
    assert cleaned["user_email"] == "finance@finova.ai"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["password"] == "[REDACTED]"
    assert cleaned["nested"]["amount"] == 5000


@pytest.mark.asyncio
async def test_audit_hash_chain_and_verification():
    logger = AuditLogger(db=None)
    org_id = "org_audit_test"

    # Log 3 chained events
    e1 = await logger.log(
        event_type=AuditEventType.PROCESSING_STARTED,
        organization_id=org_id,
        actor="system",
        message="Started reconciliation run",
    )
    e2 = await logger.log(
        event_type=AuditEventType.AI_INVESTIGATION_COMPLETED,
        organization_id=org_id,
        actor="ai_engine",
        message="AI investigated transaction",
    )
    e3 = await logger.log(
        event_type=AuditEventType.PROCESSING_COMPLETED,
        organization_id=org_id,
        actor="system",
        message="Reconciliation run finished",
    )

    assert e1.event_hash is not None
    assert e2.previous_hash == e1.event_hash
    assert e3.previous_hash == e2.event_hash

    # Verify integrity
    integrity = await logger.verify_integrity(org_id)
    assert integrity["verified"] is True
    assert integrity["total_events"] == 3
