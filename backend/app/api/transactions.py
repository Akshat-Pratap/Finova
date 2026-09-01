"""Finova — Transactions API Routes."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db, is_connected
from app.core.auth_middleware import AuthenticatedContext, get_auth_context
from app.services.memory_store import memory_results, memory_exceptions, memory_audit_logs
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


@router.get("", summary="List and search transactions")
async def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    processing_run_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """List reconciliation results with advanced filtering, search, and pagination."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"

    query: Dict[str, Any] = {}
    if org_id and org_id != "org_default":
        query["organization_id"] = org_id
    if status:
        query["status"] = status.upper()
    if processing_run_id:
        query["processing_run_id"] = processing_run_id
    if min_amount is not None or max_amount is not None:
        amount_query: Dict[str, Any] = {}
        if min_amount is not None:
            amount_query["$gte"] = min_amount
        if max_amount is not None:
            amount_query["$lte"] = max_amount
        query["actual_amount"] = amount_query

    if search:
        query["$or"] = [
            {"transaction_id": {"$regex": search, "$options": "i"}},
            {"customer_id": {"$regex": search, "$options": "i"}},
            {"invoice_id": {"$regex": search, "$options": "i"}},
        ]

    if db is not None:
        cursor = db.reconciliation_results.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            doc.pop("_id", None)
        total = await db.reconciliation_results.count_documents(query)
        return {"success": True, "transactions": docs, "total": total, "limit": limit, "skip": skip}

    # In-memory search fallback
    all_results = []
    for r_list in memory_results.values():
        for r in r_list:
            if org_id and org_id != "org_default" and r.get("organization_id") != org_id:
                continue
            if status and r.get("status") != status.upper():
                continue
            if processing_run_id and r.get("processing_run_id") != processing_run_id:
                continue
            if search:
                s_lower = search.lower()
                if s_lower not in str(r.get("transaction_id", "")).lower() and s_lower not in str(r.get("customer_id", "")).lower():
                    continue
            all_results.append(r.copy())

    all_results.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return {
        "success": True,
        "transactions": all_results[skip:skip+limit],
        "total": len(all_results),
        "limit": limit,
        "skip": skip,
    }


@router.get("/{transaction_id}", summary="Get detailed transaction record")
async def get_transaction(
    transaction_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Get full transaction evidence tree: result, matching signals, linked exceptions, and audit history."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"

    query: Dict[str, Any] = {"transaction_id": transaction_id}
    if org_id and org_id != "org_default":
        query["organization_id"] = org_id

    doc = None
    exception_doc = None
    audit_events = []

    if db is not None:
        doc = await db.reconciliation_results.find_one(query)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
        doc.pop("_id", None)

        # Linked exception
        exception_doc = await db.exceptions.find_one({"transaction_id": transaction_id})
        if exception_doc:
            exception_doc.pop("_id", None)

        # Audit events
        audit_cursor = db.audit_logs.find({"entity_id": transaction_id}).sort("created_at", -1).limit(20)
        audit_docs = await audit_cursor.to_list(length=20)
        for a in audit_docs:
            a.pop("_id", None)
            audit_events.append(a)

    else:
        for r_list in memory_results.values():
            for r in r_list:
                if r.get("transaction_id") == transaction_id:
                    doc = r.copy()
                    doc.pop("_id", None)
                    break
            if doc:
                break

        if not doc:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

        for e in memory_exceptions.values():
            if e.get("transaction_id") == transaction_id:
                exception_doc = e.copy()
                exception_doc.pop("_id", None)
                break

        audit_events = [a for a in memory_audit_logs if a.get("entity_id") == transaction_id]

    return {
        "success": True,
        "transaction": doc,
        "linked_exception": exception_doc,
        "audit_trail": audit_events,
    }
