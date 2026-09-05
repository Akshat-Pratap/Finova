"""Finova — Reconciliation API Routes."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.database import get_db, is_connected
from app.core.auth_middleware import AuthenticatedContext, get_auth_context
from app.services.workflow_controller import WorkflowController
from app.services.memory_store import memory_runs
from app.services.background_runner import BackgroundJobRunner
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reconciliation", tags=["Reconciliation"])


class RunRequest(BaseModel):
    """Request to start a reconciliation run."""
    source: str = "synthetic"  # synthetic | dataset | uploaded
    dataset_id: Optional[str] = None
    num_records: int = 250
    seed: int = 42
    dataset_name: Optional[str] = None
    idempotency_key: Optional[str] = None
    async_mode: bool = False


@router.post(
    "/run",
    summary="Start a reconciliation run (Synchronous or Background)",
    description="Starts reconciliation for a real dataset or synthetic demo dataset.",
)
async def start_reconciliation(
    request: RunRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Start reconciliation job."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    user_id = ctx.user_id if ctx else "system"
    controller = WorkflowController(db)

    # Async background processing option
    if request.async_mode:
        temp_run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        # Fetch initial count if possible
        total_rec = 0
        if request.source == "dataset" and request.dataset_id and db is not None:
            ds_doc = await db.datasets.find_one({"dataset_id": request.dataset_id})
            if ds_doc:
                total_rec = ds_doc.get("record_count", 0)

        job = BackgroundJobRunner.create_job(
            organization_id=org_id,
            run_id=temp_run_id,
            description=f"Reconciliation for {request.source}",
        )
        job.records_total = total_rec

        async def _async_worker():
            if request.source == "dataset" and request.dataset_id:
                run, results, analytics = await controller.run_from_dataset(
                    dataset_id=request.dataset_id,
                    organization_id=org_id,
                    idempotency_key=request.idempotency_key,
                    triggered_by=user_id,
                    job=job,
                )
            else:
                run, results, analytics = await controller.run_synthetic(
                    num_records=min(request.num_records, 5000),
                    seed=request.seed,
                    organization_id=org_id,
                )
            return {
                "run_id": run.run_id,
                "status": run.status.value,
                "dataset_id": request.dataset_id,
                "total_records": run.records_valid,
                "records_processed": run.records_valid,
                "records_matched": run.records_matched,
                "match_rate": run.match_rate,
                "analytics": analytics,
            }

        BackgroundJobRunner.spawn_task(job.job_id, _async_worker)
        return {
            "success": True,
            "async": True,
            "job_id": job.job_id,
            "run_id": temp_run_id,
            "dataset_id": request.dataset_id,
            "status": "QUEUED",
            "total_records": total_rec,
            "message": "Reconciliation job started in background.",
        }

    # Synchronous processing
    try:
        if request.source == "dataset" and request.dataset_id:
            run, results, analytics = await controller.run_from_dataset(
                dataset_id=request.dataset_id,
                organization_id=org_id,
                idempotency_key=request.idempotency_key,
                triggered_by=user_id,
            )
        else:
            run, results, analytics = await controller.run_synthetic(
                num_records=min(request.num_records, 5000),
                seed=request.seed,
                organization_id=org_id,
            )

        return {
            "success": True,
            "run_id": run.run_id,
            "dataset_id": run.dataset_id,
            "status": run.status.value,
            "total_records": run.records_valid,
            "records_processed": run.records_valid,
            "records_matched": run.records_matched,
            "records_ai_reviewed": run.records_ai_reviewed,
            "records_manual_review": run.records_manual_review,
            "records_duplicate": run.records_duplicate,
            "records_mismatch": run.records_mismatch,
            "exceptions_created": analytics.get("exception_count", 0),
            "match_rate": run.match_rate,
            "average_confidence": run.average_confidence,
            "processing_time_seconds": run.processing_time_seconds,
            "analytics": analytics,
        }
    except Exception as exc:
        logger.error("Reconciliation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RECONCILIATION_FAILED", "message": str(exc)},
        )


@router.get(
    "/job/{job_id}",
    summary="Get background job status & live progress",
)
async def get_job_status(job_id: str):
    """Poll the status of an asynchronous background job."""
    job = BackgroundJobRunner.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return {"success": True, "job": job.to_dict()}


@router.get(
    "/runs/{run_id}",
    summary="Get reconciliation run status & progress (REST alias)",
)
@router.get(
    "/{run_id}",
    summary="Get reconciliation run details",
)
async def get_run(
    run_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Retrieve reconciliation run details and live progress metrics."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else None
    query: Dict[str, Any] = {"run_id": run_id}
    if org_id and org_id != "org_default":
        query["organization_id"] = org_id

    doc = None
    if db is not None:
        doc = await db.processing_runs.find_one(query)
    else:
        doc = memory_runs.get(run_id)

    # Check background runner for live in-flight updates
    bg_job = BackgroundJobRunner.get_job_by_run_id(run_id)

    if not doc and not bg_job:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    if not doc and bg_job:
        job_d = bg_job.to_dict()
        return {
            "success": True,
            "run_id": run_id,
            "dataset_id": getattr(bg_job, "dataset_id", None),
            "status": bg_job.status.value,
            "total_records": bg_job.records_total,
            "processed_records": bg_job.records_processed,
            "progress_percent": bg_job.progress_percent,
            "matched_records": bg_job.matched_records,
            "unmatched_records": bg_job.unmatched_records,
            "exception_count": bg_job.exception_count,
            "ai_investigated": bg_job.ai_investigated,
            "processing_rate": bg_job.processing_rate,
            "elapsed_seconds": bg_job.elapsed_seconds,
            "error": bg_job.error,
            "organization_id": bg_job.organization_id,
            "run": job_d,
        }

    doc = doc.copy()
    doc.pop("_id", None)

    # Merge live background job stats if running
    status_val = doc.get("status", "QUEUED")
    total_records = doc.get("records_total", doc.get("records_valid", 0))
    processed_records = doc.get("records_processed", doc.get("records_valid", 0))
    progress_pct = doc.get("progress_percent", 100.0 if status_val in ("COMPLETED", "NO_COUNTERPART_SOURCE") else 0.0)
    matched_records = doc.get("records_matched", 0)
    unmatched_records = doc.get("records_unmatched", 0)
    exception_cnt = doc.get("records_manual_review", 0) + doc.get("records_ai_reviewed", 0)
    ai_investigated = doc.get("records_ai_reviewed", 0)
    proc_rate = doc.get("processing_rate", 0.0)
    elapsed_sec = doc.get("elapsed_seconds", doc.get("processing_time_seconds", 0.0))

    if bg_job and status_val == "PROCESSING":
        status_val = bg_job.status.value
        total_records = bg_job.records_total or total_records
        processed_records = bg_job.records_processed or processed_records
        progress_pct = bg_job.progress_percent or progress_pct
        matched_records = bg_job.matched_records or matched_records
        unmatched_records = bg_job.unmatched_records or unmatched_records
        exception_cnt = bg_job.exception_count or exception_cnt
        ai_investigated = bg_job.ai_investigated or ai_investigated
        proc_rate = bg_job.processing_rate or proc_rate
        elapsed_sec = bg_job.elapsed_seconds or elapsed_sec

    return {
        "success": True,
        "run_id": doc.get("run_id", run_id),
        "dataset_id": doc.get("dataset_id"),
        "status": status_val,
        "total_records": total_records,
        "processed_records": processed_records,
        "progress_percent": progress_pct,
        "matched_records": matched_records,
        "unmatched_records": unmatched_records,
        "exception_count": exception_cnt,
        "ai_investigated": ai_investigated,
        "processing_rate": proc_rate,
        "elapsed_seconds": elapsed_sec,
        "error": doc.get("error_message") or doc.get("error"),
        "organization_id": doc.get("organization_id"),
        "run": doc,
    }


@router.get(
    "",
    summary="List reconciliation runs for organization",
)
async def list_runs(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """List recent reconciliation runs in reverse chronological order."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    query = {"organization_id": org_id} if org_id and org_id != "org_default" else {}

    if db is not None:
        cursor = db.processing_runs.find(query).sort("started_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            doc.pop("_id", None)
        total = await db.processing_runs.count_documents(query)
        return {"success": True, "runs": docs, "total": total}

    all_runs = [d.copy() for d in memory_runs.values() if not org_id or d.get("organization_id") == org_id]
    all_runs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return {"success": True, "runs": all_runs[skip:skip+limit], "total": len(all_runs)}
