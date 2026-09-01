"""Finova — Audit Logs API Routes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db, is_connected
from app.core.auth_middleware import AuthenticatedContext, get_auth_context
from app.services.audit_logger import AuditLogger
from app.services.memory_store import memory_audit_logs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Audit Logs"])


@router.get("/audit-logs", summary="Get audit log timeline")
async def get_audit_logs(
    processing_run_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Get chronological audit log events for active organization."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"

    query: Dict[str, Any] = {}
    if org_id and org_id != "org_default":
        query["organization_id"] = org_id
    if processing_run_id:
        query["processing_run_id"] = processing_run_id
    if event_type:
        query["event_type"] = event_type.upper()

    if db is not None:
        cursor = db.audit_logs.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            doc.pop("_id", None)
        total = await db.audit_logs.count_documents(query)
        return {"success": True, "logs": docs, "total": total}

    all_logs = [e.copy() for e in memory_audit_logs if not org_id or org_id == "org_default" or e.get("organization_id") == org_id]
    if processing_run_id:
        all_logs = [e for e in all_logs if e.get("processing_run_id") == processing_run_id]
    if event_type:
        all_logs = [e for e in all_logs if e.get("event_type") == event_type.upper()]

    all_logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"success": True, "logs": all_logs[skip:skip+limit], "total": len(all_logs)}


@router.get("/audit-logs/verify", summary="Verify cryptographic hash chain integrity")
async def verify_audit_integrity(
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Verify that the immutable hash-chain for the organization is intact."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    logger_svc = AuditLogger(db)
    result = await logger_svc.verify_integrity(org_id)
    return {"success": True, "verification": result}
