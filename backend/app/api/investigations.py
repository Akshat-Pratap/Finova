"""Finova — AI Investigations API Routes."""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db, is_connected
from app.core.auth_middleware import AuthenticatedContext, get_auth_context
from app.services.exception_manager import ExceptionManager
from app.services.ai_engine.investigator import investigate_transaction
from app.services.memory_store import memory_results, memory_exceptions
from app.models.reconciliation import ReconciliationResult
from app.models.transaction import Transaction
from app.models.audit_log import AuditEventType
from app.services.audit_logger import AuditLogger
from app.utils.helpers import dict_to_mongo
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/investigations", tags=["AI Investigations"])

_memory_investigations = {}


@router.post(
    "/{exception_id}",
    summary="Trigger AI investigation for an exception",
)
async def trigger_investigation(
    exception_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Trigger an AI investigation for a specific exception."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    manager = ExceptionManager(db)
    exc = await manager.get(exception_id, organization_id=org_id)
    if not exc:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")

    # Load reconciliation result
    result_doc = None
    if db is not None:
        result_doc = await db.reconciliation_results.find_one({"transaction_id": exc.transaction_id})
    else:
        for r_list in memory_results.values():
            for r in r_list:
                if r.get("transaction_id") == exc.transaction_id:
                    result_doc = r
                    break
            if result_doc:
                break

    if not result_doc:
        raise HTTPException(status_code=404, detail="No reconciliation result found for this exception")

    doc_clean = result_doc.copy()
    doc_clean.pop("_id", None)
    result = ReconciliationResult(**doc_clean)

    txn = Transaction(
        transaction_id=result.transaction_id,
        customer_id=result.customer_id or "UNKNOWN",
        amount=result.actual_amount or result.expected_amount or Decimal("0"),
        timestamp=result.created_at or datetime.utcnow(),
        invoice_id=result.invoice_id,
        organization_id=org_id,
    )

    audit = AuditLogger(db)
    await audit.log(
        event_type=AuditEventType.AI_INVESTIGATION_STARTED,
        organization_id=org_id,
        entity_type="exception",
        entity_id=exception_id,
        processing_run_id=exc.processing_run_id,
        message=f"Manual AI investigation triggered for {exception_id}",
    )

    investigation = await investigate_transaction(
        txn=txn,
        reconciliation_result=result,
        exception_id=exception_id,
        processing_run_id=exc.processing_run_id,
        organization_id=org_id,
    )

    await manager.update_with_ai_result(exc, investigation)

    _memory_investigations[exception_id] = dict_to_mongo(investigation)
    if db is not None:
        try:
            await db.ai_investigations.insert_one(dict_to_mongo(investigation))
        except Exception:
            pass

    await audit.log(
        AuditEventType.AI_INVESTIGATION_COMPLETED,
        organization_id=org_id,
        entity_type="exception",
        entity_id=exception_id,
        processing_run_id=exc.processing_run_id,
        message=f"AI finding: {investigation.finding} ({investigation.confidence:.0%} confidence)",
    )

    return {
        "success": True,
        "investigation_id": investigation.investigation_id,
        "finding": investigation.finding,
        "reason": investigation.reason,
        "confidence": investigation.confidence,
        "recommendation": investigation.recommendation,
        "requires_manual_review": investigation.requires_manual_review,
        "evidence": investigation.evidence,
        "provider": investigation.provider,
        "prompt_version": investigation.prompt_version,
        "latency_ms": investigation.latency_ms,
        "is_fallback": investigation.is_fallback,
    }


@router.get(
    "/results/{exception_id}",
    summary="Get AI investigation results for an exception",
)
async def get_investigation(
    exception_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Retrieve AI investigation results."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else None
    query = {"exception_id": exception_id}
    if org_id and org_id != "org_default":
        query["organization_id"] = org_id

    doc = None
    if db is not None:
        doc = await db.ai_investigations.find_one(query)
    else:
        doc = _memory_investigations.get(exception_id)

    if not doc:
        raise HTTPException(status_code=404, detail="No investigation found")

    doc_clean = doc.copy()
    doc_clean.pop("_id", None)
    return {"success": True, "investigation": doc_clean}
