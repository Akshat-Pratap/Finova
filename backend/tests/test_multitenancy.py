"""Finova — Multi-Tenancy & RBAC Tests."""
from __future__ import annotations

import pytest
from app.models.user import UserRole
from app.services.auth_service import AuthService
from app.services.org_service import OrgService
from app.core.auth_middleware import require_roles, AuthenticatedContext
from app.models.user import User


@pytest.mark.asyncio
async def test_organization_member_invitation_and_rbac():
    auth_svc = AuthService(db=None)
    org_svc = OrgService(db=None)

    # Bootstrap owner
    owner, org, _, _ = await auth_svc.register(
        email="owner@tenant.com",
        password="Password123!",
        full_name="Owner User",
        organization_name="Tenant Alpha",
    )

    # Invite analyst
    membership = await org_svc.invite_member(
        organization_id=org.organization_id,
        email="analyst@tenant.com",
        role=UserRole.FINANCE_ANALYST,
        invited_by=owner.user_id,
    )

    assert membership.organization_id == org.organization_id
    assert membership.user_email == "analyst@tenant.com"
    assert membership.role == UserRole.FINANCE_ANALYST

    # List members
    members = await org_svc.list_members(org.organization_id)
    assert len(members) >= 2
    roles = [m["role"] for m in members]
    assert UserRole.OWNER in roles or UserRole.OWNER.value in roles
    assert UserRole.FINANCE_ANALYST in roles or UserRole.FINANCE_ANALYST.value in roles


@pytest.mark.asyncio
async def test_org_settings_update():
    org_svc = OrgService(db=None)
    org, _ = await org_svc.create_organization(
        name="Global Hedge Fund",
        base_currency="USD",
        owner_id="usr_fund_owner",
    )

    updated_org = await org_svc.update_settings(
        organization_id=org.organization_id,
        base_currency="USD",
        auto_reconcile_threshold=0.92,
        amount_tolerance=1.50,
    )

    assert updated_org.settings.base_currency == "USD"
    assert updated_org.settings.auto_reconcile_threshold == 0.92
    assert updated_org.settings.amount_tolerance == 1.50
