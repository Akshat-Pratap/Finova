"""Finova — Organizations & Multi-Tenancy API Routes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.database import get_db, is_connected
from app.core.auth_middleware import AuthenticatedContext, get_auth_context, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.organization import Organization, OrgSettings
from app.services.org_service import OrgService
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


class CreateOrgRequest(BaseModel):
    name: str
    base_currency: str = "INR"
    settings: Optional[Dict[str, Any]] = None


class UpdateSettingsRequest(BaseModel):
    base_currency: Optional[str] = None
    auto_reconcile_threshold: Optional[float] = None
    ai_review_threshold: Optional[float] = None
    fee_tolerance_percent: Optional[float] = None
    tax_tolerance_percent: Optional[float] = None
    date_tolerance_days: Optional[int] = None
    partial_payment_tolerance_percent: Optional[float] = None
    confidence_weights: Optional[Dict[str, float]] = None


class AddMemberRequest(BaseModel):
    email: str
    role: UserRole = UserRole.FINANCE_ANALYST


@router.get(
    "",
    summary="List current user's organizations",
)
async def list_my_organizations(user: User = Depends(get_current_user)):
    """Retrieve all organizations where the user has active membership."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_svc = OrgService(db)
    orgs = await org_svc.list_user_organizations(user.user_id)
    return {"success": True, "organizations": orgs}


@router.post(
    "",
    summary="Create a new organization",
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    request: CreateOrgRequest,
    user: User = Depends(get_current_user),
):
    """Create a new tenant organization. The creating user becomes OWNER."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_svc = OrgService(db)
    org, membership = await org_svc.create_organization(
        name=request.name,
        user_id=user.user_id,
        base_currency=request.base_currency,
        settings_dict=request.settings,
    )

    return {
        "success": True,
        "organization": dict_to_mongo(org),
        "role": membership.role.value,
    }


@router.get(
    "/{org_id}",
    summary="Get organization details",
)
async def get_organization(
    org_id: str,
    ctx: AuthenticatedContext = Depends(get_auth_context),
):
    """Get active organization information and tolerances."""
    return {
        "success": True,
        "organization": dict_to_mongo(ctx.organization),
        "current_role": ctx.role.value,
    }


@router.patch(
    "/{org_id}/settings",
    summary="Update organization reconciliation settings",
)
async def update_settings(
    org_id: str,
    request: UpdateSettingsRequest,
    ctx: AuthenticatedContext = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
):
    """Update organization reconciliation rules, tolerances, weights, or base currency."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_svc = OrgService(db)
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    updated_org = await org_svc.update_settings(
        org_id=org_id,
        new_settings=update_data,
        actor_id=ctx.user.email,
    )

    if not updated_org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {"success": True, "organization": dict_to_mongo(updated_org)}


@router.get(
    "/{org_id}/members",
    summary="List organization members",
)
async def list_members(
    org_id: str,
    ctx: AuthenticatedContext = Depends(get_auth_context),
):
    """List members and their roles in the organization."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_svc = OrgService(db)
    members = await org_svc.list_members(org_id)
    return {"success": True, "members": members}


@router.post(
    "/{org_id}/members",
    summary="Invite or add a member to the organization",
)
async def add_member(
    org_id: str,
    request: AddMemberRequest,
    ctx: AuthenticatedContext = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
):
    """Invite an existing user to the organization with a designated role."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_svc = OrgService(db)
    try:
        result = await org_svc.add_member(
            org_id=org_id,
            user_email=request.email,
            role=request.role,
            inviter_id=ctx.user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"success": True, "member": result}
