"""Finova — Analytics API Routes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db, is_connected
from app.core.auth_middleware import AuthenticatedContext, get_auth_context
from app.services.analytics_engine import get_summary_analytics
from app.services.memory_store import memory_runs as _memory_runs, memory_results as _memory_results
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/summary", summary="Get aggregate analytics summary for organization")
async def analytics_summary(
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Aggregate reconciliation metrics across all runs for the tenant organization."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    summary = await get_summary_analytics(db, organization_id=org_id)
    return {"success": True, "summary": summary}


@router.get("/metrics", summary="Get detailed metrics for a run")
async def run_metrics(
    run_id: Optional[str] = Query(None),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Get detailed metrics & status breakdown for a specific or latest run."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"

    query: Dict[str, Any] = {}
    if org_id and org_id != "org_default":
        query["organization_id"] = org_id
    if run_id:
        query["run_id"] = run_id

    doc = None
    if db is not None:
        doc = await db.processing_runs.find_one(query, sort=[("started_at", -1)])
        if not doc:
            raise HTTPException(status_code=404, detail="No reconciliation runs found")
        doc.pop("_id", None)

        pipeline = [
            {"$match": {"processing_run_id": doc["run_id"]}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$confidence"},
            }},
        ]
        cursor = db.reconciliation_results.aggregate(pipeline)
        breakdown_docs = await cursor.to_list(length=20)
        breakdown = {d["_id"]: {"count": d["count"], "avg_confidence": round(d["avg_confidence"] or 0, 3)} for d in breakdown_docs}
    else:
        runs = [r for r in _memory_runs.values() if not org_id or org_id == "org_default" or r.get("organization_id") == org_id]
        if run_id:
            runs = [r for r in runs if r.get("run_id") == run_id]
        if not runs:
            raise HTTPException(status_code=404, detail="No reconciliation runs found")
        runs.sort(key=lambda x: str(x.get("started_at", "")), reverse=True)
        doc = runs[0].copy()
        doc.pop("_id", None)

        results = _memory_results.get(doc["run_id"], [])
        breakdown = {}
        for r in results:
            st = r.get("status", "UNKNOWN")
            if st not in breakdown:
                breakdown[st] = {"count": 0, "avg_confidence": 0.0, "_sum": 0.0}
            breakdown[st]["count"] += 1
            breakdown[st]["_sum"] += r.get("confidence", 0.0)
        for st, data in breakdown.items():
            data["avg_confidence"] = round(data["_sum"] / data["count"], 3) if data["count"] else 0.0
            data.pop("_sum", None)

    return {
        "success": True,
        "run": doc,
        "status_breakdown": breakdown,
    }
