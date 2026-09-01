"""Finova — Auth & RBAC Dependencies.

Extracts authenticated User and Organization context from headers/cookies and enforces server-side RBAC.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional, Tuple
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_db, is_connected
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.models.organization import Organization, OrgSettings
from app.models.membership import Membership
from app.services.auth_service import AuthService
from app.services.org_service import OrgService

logger = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)

# Role hierarchy for inheritance checks
ROLE_HIERARCHY = {
    UserRole.OWNER: 5,
    UserRole.ADMIN: 4,
    UserRole.FINANCE_MANAGER: 3,
    UserRole.FINANCE_ANALYST: 2,
    UserRole.VIEWER: 1,
}


async def get_current_user_optional(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    finova_access_token: Optional[str] = Cookie(None),
) -> Optional[User]:
    """Extract and validate the current user from Bearer header or cookie if present."""
    token = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif finova_access_token:
        token = finova_access_token

    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    auth_svc = AuthService(db)
    user = await auth_svc.get_user_by_id(user_id)
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Enforce authentication on protected endpoints."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Authentication required. Please login."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_DISABLED", "message": "Your user account is inactive."},
        )
    return user


class AuthenticatedContext:
    """Container holding authenticated User, Organization, and current Role."""

    def __init__(self, user: User, organization: Organization, role: UserRole):
        self.user = user
        self.organization = organization
        self.role = role
        self.org_id = organization.organization_id
        self.user_id = user.user_id


async def get_auth_context(
    user: User = Depends(get_current_user),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
) -> AuthenticatedContext:
    """Extract organization context and verify user's membership and role in that tenant."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    auth_svc = AuthService(db)
    org_svc = OrgService(db)

    target_org_id = x_organization_id
    if not target_org_id:
        # Fall back to user's primary org
        primary_org, role = await auth_svc.get_primary_org_for_user(user.user_id)
        if not primary_org:
            # Create default organization if none exists
            primary_org, _ = await org_svc.create_organization(
                name=f"{user.full_name}'s Org",
                user_id=user.user_id,
            )
            role = UserRole.OWNER
        return AuthenticatedContext(user=user, organization=primary_org, role=role)

    # Verify target organization
    org = await org_svc.get_organization(target_org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORG_NOT_FOUND", "message": f"Organization '{target_org_id}' does not exist."},
        )

    # Verify membership
    memberships = await org_svc.list_user_organizations(user.user_id)
    matched = next((m for m in memberships if m["organization"]["organization_id"] == target_org_id), None)
    if not matched and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "TENANT_ACCESS_DENIED", "message": "You are not a member of this organization."},
        )

    role_str = matched["role"] if matched else "VIEWER"
    role = UserRole(role_str) if isinstance(role_str, str) else role_str
    return AuthenticatedContext(user=user, organization=org, role=role)


def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory to enforce minimum role permissions.
    Example: Depends(require_roles(UserRole.OWNER, UserRole.ADMIN))
    """
    async def _role_checker(ctx: AuthenticatedContext = Depends(get_auth_context)) -> AuthenticatedContext:
        min_allowed_level = min(ROLE_HIERARCHY.get(r, 0) for r in allowed_roles) if allowed_roles else 1
        user_level = ROLE_HIERARCHY.get(ctx.role, 0)

        if user_level < min_allowed_level and not ctx.user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Operation requires one of {[r.value for r in allowed_roles]} role(s). Your role is {ctx.role.value}.",
                },
            )
        return ctx

    return _role_checker
