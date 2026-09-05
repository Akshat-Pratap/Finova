"""Finova — Dataset Ingestion & Validation API Routes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.core.database import get_db, is_connected
from app.core.security import is_allowed_file, sanitize_filename
from app.core.config import settings
from app.core.auth_middleware import AuthenticatedContext, get_auth_context, get_current_user_optional
from app.models.dataset import Dataset, DatasetStatus
from app.services.dataset_service import DatasetService
from app.services.workflow_controller import WorkflowController
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/datasets", tags=["Datasets"])


class ValidateDatasetRequest(BaseModel):
    column_mapping: Optional[Dict[str, str]] = None


@router.post(
    "/upload",
    summary="Upload a financial dataset (CSV/JSON)",
    description="Uploads a dataset file, validates format, detects column headers, and saves for reconciliation.",
)
async def upload_dataset(
    file: UploadFile = File(...),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Upload a real financial dataset file."""
    filename = sanitize_filename(file.filename or "upload")

    if not is_allowed_file(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_FILE_TYPE", "message": "Only CSV and JSON files are supported."},
        )

    content = await file.read()

    if len(content) > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": f"File exceeds {settings.max_upload_size // 1024 // 1024}MB limit."},
        )

    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    user_id = ctx.user_id if ctx else "anonymous"

    service = DatasetService(db)
    try:
        dataset, mapping, sample = await service.upload_dataset(
            content=content,
            filename=filename,
            organization_id=org_id,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "PARSE_ERROR", "message": str(exc)},
        )

    return {
        "success": True,
        "dataset_id": dataset.dataset_id,
        "filename": dataset.filename,
        "source_type": dataset.source_type,
        "record_count": dataset.record_count,
        "status": dataset.processing_status.value,
        "detected_mapping": mapping,
        "sample_rows": sample,
        "message": f"Successfully parsed {dataset.record_count} records from {filename}.",
    }


@router.get(
    "",
    summary="List uploaded datasets for organization",
)
async def list_datasets(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """List datasets in reverse chronological order."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    service = DatasetService(db)
    datasets, total = await service.list_datasets(org_id, limit=limit, skip=skip)
    return {
        "success": True,
        "datasets": [dict_to_mongo(d) for d in datasets],
        "total": total,
        "limit": limit,
        "skip": skip,
    }


@router.get(
    "/{dataset_id}",
    summary="Get dataset details & validation status",
)
async def get_dataset(
    dataset_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Get single dataset details."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    service = DatasetService(db)
    dataset = await service.get_dataset(dataset_id, organization_id=org_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    return {"success": True, "dataset": dict_to_mongo(dataset)}


@router.delete(
    "/{dataset_id}",
    summary="Permanently delete a dataset and its records",
)
async def delete_dataset(
    dataset_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Permanently delete a dataset and all associated records from MongoDB Atlas and memory."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    user_id = ctx.user_id if ctx else "anonymous"

    service = DatasetService(db)
    deleted = await service.delete_dataset(dataset_id, organization_id=org_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

    return {
        "success": True,
        "message": f"Dataset '{dataset_id}' and all its stored records were permanently deleted.",
    }


@router.post(
    "/{dataset_id}/validate",
    summary="Validate dataset and preview data hygiene",
)
async def validate_dataset_endpoint(
    dataset_id: str,
    request: ValidateDatasetRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Validate dataset records using selected column mapping and return validation report."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    user_id = ctx.user_id if ctx else "anonymous"

    service = DatasetService(db)
    try:
        report = await service.validate_dataset(
            dataset_id=dataset_id,
            organization_id=org_id,
            custom_mapping=request.column_mapping,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": str(exc)})

    return {"success": True, "validation_report": report}


@router.post(
    "/generate",
    summary="Generate synthetic dataset (Sandbox / Demo)",
    description="Generate and process a synthetic dataset for demo, benchmarking, or testing.",
)
async def generate_dataset(
    num_records: int = Query(250, ge=10, le=5000),
    seed: int = Query(42),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Generate and immediately reconcile a synthetic dataset."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    controller = WorkflowController(db)
    run, results, analytics = await controller.run_synthetic(
        num_records=num_records,
        seed=seed,
        organization_id=org_id,
    )

    return {
        "success": True,
        "run_id": run.run_id,
        "records_generated": num_records,
        "records_processed": run.records_valid,
        "analytics": analytics,
    }
