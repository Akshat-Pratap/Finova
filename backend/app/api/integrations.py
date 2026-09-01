"""Finova — Payment & Bank Integrations API Routes."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.database import get_db, is_connected
from app.core.security import mask_secret
from app.core.auth_middleware import AuthenticatedContext, get_auth_context, require_roles
from app.models.user import UserRole
from app.models.integration import Integration, IntegrationProviderType, IntegrationStatus
from app.models.audit_log import AuditEventType
from app.services.audit_logger import AuditLogger
from app.services.integrations.razorpay_provider import RazorpayProvider
from app.services.workflow_controller import WorkflowController
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])

_memory_integrations: Dict[str, dict] = {}


class ConnectIntegrationRequest(BaseModel):
    provider: IntegrationProviderType = IntegrationProviderType.RAZORPAY
    key_id: str
    key_secret: str


@router.get("", summary="List organization integrations")
async def list_integrations(
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """List all connected payment gateways and bank feeds."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"

    if db is not None:
        cursor = db.integrations.find({"organization_id": org_id})
        docs = await cursor.to_list(length=50)
        for doc in docs:
            doc.pop("_id", None)
            doc.pop("config", None)  # Never expose raw secrets in list response
        return {"success": True, "integrations": docs}

    integrations = [
        {
            "integration_id": d["integration_id"],
            "organization_id": d["organization_id"],
            "provider": d["provider"],
            "status": d["status"],
            "masked_key_id": d.get("masked_key_id"),
            "last_sync_at": d.get("last_sync_at"),
            "last_sync_records": d.get("last_sync_records", 0),
            "created_at": d.get("created_at"),
        }
        for d in _memory_integrations.values()
        if not org_id or org_id == "org_default" or d.get("organization_id") == org_id
    ]
    return {"success": True, "integrations": integrations}


@router.post("/connect", summary="Connect a payment or bank provider")
async def connect_integration(
    request: ConnectIntegrationRequest,
    ctx: Optional[AuthenticatedContext] = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
):
    """Connect a new payment provider (e.g. Razorpay)."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    user_email = ctx.user.email if ctx else "admin"

    provider = RazorpayProvider(key_id=request.key_id, key_secret=request.key_secret)
    is_ok, msg = await provider.test_connection()

    integration_id = f"int_{uuid.uuid4().hex[:12]}"
    integration = Integration(
        integration_id=integration_id,
        organization_id=org_id,
        provider=request.provider,
        status=IntegrationStatus.CONNECTED if is_ok else IntegrationStatus.ERROR,
        config={"key_id": request.key_id, "key_secret": request.key_secret},
        masked_key_id=mask_secret(request.key_id),
        last_error=None if is_ok else msg,
        created_at=datetime.utcnow(),
    )

    _memory_integrations[integration_id] = dict_to_mongo(integration)

    if db is not None:
        await db.integrations.replace_one(
            {"organization_id": org_id, "provider": request.provider.value},
            dict_to_mongo(integration),
            upsert=True,
        )

    audit = AuditLogger(db)
    await audit.log(
        event_type=AuditEventType.INTEGRATION_CONNECTED,
        organization_id=org_id,
        entity_type="integration",
        entity_id=integration_id,
        actor=user_email,
        message=f"Connected {request.provider.value} provider ({provider.mode} mode).",
    )

    return {
        "success": True,
        "integration_id": integration_id,
        "provider": request.provider.value,
        "status": integration.status.value,
        "mode": provider.mode,
        "message": msg,
    }


@router.post("/{integration_id}/test", summary="Test integration connection")
async def test_integration(
    integration_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Test connection status for an active integration."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    integration_doc = _memory_integrations.get(integration_id)
    if db is not None:
        integration_doc = await db.integrations.find_one({"integration_id": integration_id})

    if not integration_doc:
        raise HTTPException(status_code=404, detail="Integration not found")

    cfg = integration_doc.get("config", {})
    provider = RazorpayProvider(key_id=cfg.get("key_id"), key_secret=cfg.get("key_secret"))
    is_ok, msg = await provider.test_connection()

    return {"success": is_ok, "mode": provider.mode, "message": msg}


@router.post("/{integration_id}/sync", summary="Synchronize transactions from provider")
async def sync_integration(
    integration_id: str,
    count: int = Query(50, ge=5, le=500),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Fetch recent payments and settlements from the gateway and trigger reconciliation."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    user_email = ctx.user.email if ctx else "admin"

    integration_doc = _memory_integrations.get(integration_id)
    if db is not None:
        integration_doc = await db.integrations.find_one({"integration_id": integration_id})

    if not integration_doc:
        # Fallback to default Razorpay provider
        provider = RazorpayProvider()
    else:
        cfg = integration_doc.get("config", {})
        provider = RazorpayProvider(key_id=cfg.get("key_id"), key_secret=cfg.get("key_secret"))

    # Fetch live or sandbox records
    payments = await provider.fetch_payments(count=count)
    settlements = await provider.fetch_settlements(count=max(5, count // 5))

    controller = WorkflowController(db)
    run, results, analytics = await controller.run_from_data(
        txn_records=payments,
        inv_records=[],
        bank_records=[],
        sett_records=settlements,
        dataset_name=f"razorpay_sync_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
        organization_id=org_id,
        triggered_by=user_email,
    )

    now = datetime.utcnow()
    if integration_doc:
        integration_doc["last_sync_at"] = now
        integration_doc["last_sync_records"] = len(payments)
        if db is not None:
            await db.integrations.update_one(
                {"integration_id": integration_id},
                {"$set": {"last_sync_at": now, "last_sync_records": len(payments)}},
            )

    audit = AuditLogger(db)
    await audit.log(
        event_type=AuditEventType.INTEGRATION_SYNCED,
        organization_id=org_id,
        entity_type="integration",
        entity_id=integration_id,
        actor=user_email,
        message=f"Synced {len(payments)} payments from Razorpay. Matched {run.records_matched} records.",
        metadata={"payments_synced": len(payments), "run_id": run.run_id},
    )

    return {
        "success": True,
        "run_id": run.run_id,
        "payments_imported": len(payments),
        "settlements_imported": len(settlements),
        "records_matched": run.records_matched,
        "match_rate": run.match_rate,
        "analytics": analytics,
    }


@router.delete("/{integration_id}", summary="Disconnect integration")
async def disconnect_integration(
    integration_id: str,
    ctx: Optional[AuthenticatedContext] = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
):
    """Disconnect and remove integration credentials."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"
    user_email = ctx.user.email if ctx else "admin"

    if integration_id in _memory_integrations:
        del _memory_integrations[integration_id]

    if db is not None:
        await db.integrations.delete_one({"integration_id": integration_id, "organization_id": org_id})

    audit = AuditLogger(db)
    await audit.log(
        event_type=AuditEventType.INTEGRATION_DISCONNECTED,
        organization_id=org_id,
        entity_type="integration",
        entity_id=integration_id,
        actor=user_email,
        message="Integration disconnected.",
    )

    return {"success": True, "message": "Integration disconnected successfully."}
