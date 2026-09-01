"""Finova — Exceptions API Routes."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.database import get_db, is_connected
from app.core.auth_middleware import AuthenticatedContext, get_auth_context
from app.services.exception_manager import ExceptionManager
from app.models.exception import ExceptionStatus
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/exceptions", tags=["Exceptions"])


class ResolveRequest(BaseModel):
    resolution: str
    notes: Optional[str] = None


class AssignRequest(BaseModel):
    assignee_email: str


class AddNoteRequest(BaseModel):
    content: str


class AdjustmentRequest(BaseModel):
    amount: Decimal
    currency: str = "INR"
    reason: str


@router.get("", summary="List exceptions")
async def list_exceptions(
    status: Optional[str] = Query(None),
    processing_run_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """List financial exceptions for active organization."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    manager = ExceptionManager(db)
    exc_status = None
    if status:
        try:
            exc_status = ExceptionStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    exceptions = await manager.list_exceptions(
        status=exc_status,
        processing_run_id=processing_run_id,
        organization_id=org_id,
        limit=limit,
        skip=skip,
    )

    return {
        "success": True,
        "exceptions": [dict_to_mongo(e) for e in exceptions],
        "total": len(exceptions),
    }


@router.get("/{exception_id}", summary="Get exception details")
async def get_exception(
    exception_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Get a single exception with full details and comments."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    manager = ExceptionManager(db)
    exc = await manager.get(exception_id, organization_id=org_id)
    if not exc:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")

    notes = await manager.list_notes(exception_id, organization_id=org_id)
    exc_dict = dict_to_mongo(exc)
    exc_dict["comments"] = [dict_to_mongo(n) for n in notes]

    return {"success": True, "exception": exc_dict}


@router.post("/{exception_id}/resolve", summary="Resolve an exception")
async def resolve_exception(
    exception_id: str,
    request: ResolveRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Resolve a financial exception."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    actor = ctx.user.email if ctx else "finance_officer"

    manager = ExceptionManager(db)
    exc = await manager.resolve(
        exception_id=exception_id,
        resolution=request.resolution,
        actor=actor,
        notes=request.notes,
        organization_id=org_id,
    )
    if not exc:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")

    return {"success": True, "exception": dict_to_mongo(exc)}


@router.post("/{exception_id}/reject", summary="Reject an exception")
async def reject_exception(
    exception_id: str,
    request: ResolveRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Reject an exception (confirm it as a real discrepancy)."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    actor = ctx.user.email if ctx else "finance_officer"

    manager = ExceptionManager(db)
    exc = await manager.reject(
        exception_id=exception_id,
        actor=actor,
        notes=request.notes,
        organization_id=org_id,
    )
    if not exc:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")

    return {"success": True, "exception": dict_to_mongo(exc)}


@router.post("/{exception_id}/ignore", summary="Ignore an exception")
async def ignore_exception(
    exception_id: str,
    request: ResolveRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Ignore an exception."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    actor = ctx.user.email if ctx else "finance_officer"

    manager = ExceptionManager(db)
    exc = await manager.ignore(
        exception_id=exception_id,
        actor=actor,
        notes=request.notes,
        organization_id=org_id,
    )
    if not exc:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")

    return {"success": True, "exception": dict_to_mongo(exc)}


@router.post("/{exception_id}/assign", summary="Assign exception to officer")
async def assign_exception_endpoint(
    exception_id: str,
    request: AssignRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Assign exception to a specific user email."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    actor = ctx.user.email if ctx else "system"

    manager = ExceptionManager(db)
    exc = await manager.assign(
        exception_id=exception_id,
        assignee_email=request.assignee_email,
        actor=actor,
        organization_id=org_id,
    )
    if not exc:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")

    return {"success": True, "exception": dict_to_mongo(exc)}


@router.post("/{exception_id}/notes", summary="Add comment note to exception")
async def add_exception_note(
    exception_id: str,
    request: AddNoteRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Add a user note to an exception thread."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    author = ctx.user.email if ctx else "finance_officer"
    author_id = ctx.user.user_id if ctx else None

    manager = ExceptionManager(db)
    note = await manager.add_note(
        exception_id=exception_id,
        content=request.content,
        author=author,
        author_id=author_id,
        organization_id=org_id,
    )
    return {"success": True, "note": dict_to_mongo(note)}


@router.post("/{exception_id}/adjust", summary="Record audited financial adjustment")
async def record_adjustment(
    exception_id: str,
    request: AdjustmentRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Record an audited financial adjustment without altering raw historical evidence."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    author = ctx.user.email if ctx else "finance_officer"

    manager = ExceptionManager(db)
    adj = await manager.record_adjustment(
        exception_id=exception_id,
        amount=request.amount,
        currency=request.currency,
        reason=request.reason,
        approved_by=author,
        organization_id=org_id,
    )
    return {"success": True, "adjustment": dict_to_mongo(adj)}
