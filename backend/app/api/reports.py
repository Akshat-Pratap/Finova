"""Finova — Financial Reports API Routes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.core.database import get_db, is_connected
from app.core.auth_middleware import AuthenticatedContext, get_auth_context
from app.models.report import Report, ReportType, ReportFormat
from app.models.audit_log import AuditEventType
from app.services.audit_logger import AuditLogger
from app.services.report_generator import generate_csv_report, generate_json_report
from app.services.memory_store import memory_results, memory_runs, memory_exceptions, memory_audit_logs
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


class ExportRequest(BaseModel):
    report_type: ReportType = ReportType.RECONCILIATION
    format: ReportFormat = ReportFormat.CSV
    processing_run_id: Optional[str] = None


@router.post(
    "/export",
    summary="Export financial reports (CSV / JSON)",
    description="Generate and download reconciliation results, exceptions, transactions, or audit logs.",
)
async def export_report(
    request: ExportRequest,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Export report in requested format."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    user_email = ctx.user.email if ctx else "finance_officer"

    records = []
    filename_prefix = request.report_type.value.lower()

    if request.report_type == ReportType.RECONCILIATION:
        query: Dict[str, Any] = {"organization_id": org_id}
        if request.processing_run_id:
            query["processing_run_id"] = request.processing_run_id
        if db is not None:
            cursor = db.reconciliation_results.find(query).limit(10000)
            docs = await cursor.to_list(length=10000)
            records = [dict_to_mongo(d) for d in docs]
        else:
            if request.processing_run_id and request.processing_run_id in memory_results:
                records = memory_results[request.processing_run_id]
            else:
                for r_list in memory_results.values():
                    records.extend(r_list)

    elif request.report_type == ReportType.EXCEPTIONS:
        query = {"organization_id": org_id}
        if request.processing_run_id:
            query["processing_run_id"] = request.processing_run_id
        if db is not None:
            cursor = db.exceptions.find(query).limit(10000)
            docs = await cursor.to_list(length=10000)
            records = [dict_to_mongo(d) for d in docs]
        else:
            records = list(memory_exceptions.values())

    elif request.report_type == ReportType.AUDIT_LOG:
        query = {"organization_id": org_id}
        if request.processing_run_id:
            query["processing_run_id"] = request.processing_run_id
        if db is not None:
            cursor = db.audit_logs.find(query).sort("created_at", -1).limit(10000)
            docs = await cursor.to_list(length=10000)
            records = [dict_to_mongo(d) for d in docs]
        else:
            records = [e for e in memory_audit_logs if e.get("organization_id") == org_id]

    elif request.report_type == ReportType.PROCESSING_RUN:
        query = {"organization_id": org_id}
        if db is not None:
            cursor = db.processing_runs.find(query).sort("started_at", -1).limit(500)
            docs = await cursor.to_list(length=500)
            records = [dict_to_mongo(d) for d in docs]
        else:
            records = list(memory_runs.values())

    # Log export event
    audit = AuditLogger(db)
    await audit.log(
        event_type=AuditEventType.REPORT_EXPORTED,
        organization_id=org_id,
        entity_type="report",
        actor=user_email,
        message=f"Exported {request.report_type.value} report ({len(records)} records) as {request.format.value}.",
    )

    if request.format == ReportFormat.CSV:
        csv_data = generate_csv_report(records)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="finova_{filename_prefix}_report.csv"'},
        )
    else:
        json_data = generate_json_report(records, metadata={"organization_id": org_id, "type": request.report_type.value})
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="finova_{filename_prefix}_report.json"'},
        )
