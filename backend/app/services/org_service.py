"""Finova — Organization Service.

Manages tenant organizations, user memberships, RBAC assignments, and tolerances.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.models.user import User, UserRole
from app.models.organization import Organization, OrgSettings
from app.models.membership import Membership
from app.models.audit_log import AuditEventType
from app.services.audit_logger import AuditLogger
from app.services.auth_service import _memory_orgs, _memory_memberships, _memory_users
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)


class OrgService:
    """Organization & Tenant operations."""

    def __init__(self, db=None):
        self._db = db
        self._audit = AuditLogger(db)

    async def create_organization(
        self,
        name: str,
        user_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        base_currency: str = "INR",
        settings_dict: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Organization, Membership]:
        """Create a new tenant organization and make user the OWNER."""
        effective_user_id = user_id or owner_id or "usr_owner"
        org_title = name.strip()
        slug = f"{org_title.lower().replace(' ', '-')[:30]}-{uuid.uuid4().hex[:4]}"
        settings = OrgSettings(**(settings_dict or {}))
        settings.base_currency = base_currency

        org = Organization(
            organization_id=f"org_{uuid.uuid4().hex[:12]}",
            name=org_title,
            slug=slug,
            base_currency=base_currency,
            owner_user_id=effective_user_id,
            settings=settings,
            created_at=datetime.utcnow(),
        )

        membership = Membership(
            membership_id=f"mem_{uuid.uuid4().hex[:12]}",
            user_id=effective_user_id,
            organization_id=org.organization_id,
            role=UserRole.OWNER,
            joined_at=datetime.utcnow(),
        )

        if self._db is not None:
            await self._db.organizations.insert_one(dict_to_mongo(org))
            await self._db.memberships.insert_one(dict_to_mongo(membership))
        else:
            _memory_orgs[org.organization_id] = dict_to_mongo(org)
            _memory_memberships[membership.membership_id] = dict_to_mongo(membership)

        await self._audit.log(
            event_type=AuditEventType.ORG_CREATED,
            organization_id=org.organization_id,
            entity_type="organization",
            entity_id=org.organization_id,
            actor=user_id,
            actor_id=user_id,
            message=f"Organization '{org.name}' created with base currency {base_currency}.",
        )

        return org, membership

    async def list_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """List all organizations that a user belongs to, including their role in each."""
        results = []
        if self._db is not None:
            cursor = self._db.memberships.find({"user_id": user_id})
            memberships = await cursor.to_list(length=100)
            for m in memberships:
                org_doc = await self._db.organizations.find_one({"organization_id": m["organization_id"]})
                if org_doc:
                    org_doc.pop("_id", None)
                    results.append({
                        "organization": org_doc,
                        "role": m.get("role", "VIEWER"),
                        "joined_at": m.get("joined_at"),
                    })
        else:
            for m in _memory_memberships.values():
                if m.get("user_id") == user_id:
                    org_doc = _memory_orgs.get(m["organization_id"])
                    if org_doc:
                        d = org_doc.copy()
                        d.pop("_id", None)
                        results.append({
                            "organization": d,
                            "role": m.get("role", "VIEWER"),
                            "joined_at": m.get("joined_at"),
                        })
        return results

    async def get_organization(self, org_id: str) -> Optional[Organization]:
        if self._db is not None:
            doc = await self._db.organizations.find_one({"organization_id": org_id})
            if doc:
                doc.pop("_id", None)
                return Organization(**doc)
            return None
        if org_id in _memory_orgs:
            d = _memory_orgs[org_id].copy()
            d.pop("_id", None)
            return Organization(**d)
        return None

    async def update_settings(
        self,
        organization_id: str,
        new_settings: Optional[Dict[str, Any]] = None,
        actor_id: str = "system",
        **kwargs,
    ) -> Optional[Organization]:
        """Update organization configuration (thresholds, weights, currency)."""
        org = await self.get_organization(organization_id)
        if not org:
            return None

        merged = {}
        if new_settings:
            merged.update(new_settings)
        merged.update(kwargs)

        current_settings = org.settings.model_dump()
        current_settings.update(merged)
        validated_settings = OrgSettings(**current_settings)
        org.settings = validated_settings

        if "base_currency" in merged:
            org.base_currency = merged["base_currency"]

        if self._db is not None:
            await self._db.organizations.update_one(
                {"organization_id": organization_id},
                {"$set": {
                    "settings": dict_to_mongo(validated_settings),
                    "base_currency": org.base_currency,
                }},
            )
        else:
            _memory_orgs[organization_id]["settings"] = dict_to_mongo(validated_settings)
            _memory_orgs[organization_id]["base_currency"] = org.base_currency

        await self._audit.log(
            event_type=AuditEventType.SETTINGS_CHANGED,
            organization_id=organization_id,
            entity_type="organization",
            entity_id=organization_id,
            actor=actor_id,
            actor_id=actor_id,
            message="Organization reconciliation settings updated.",
            metadata=merged,
        )
        return org

    async def invite_member(
        self,
        organization_id: str,
        email: str,
        role: UserRole,
        invited_by: str = "system",
    ) -> Membership:
        """Invite/add member to an organization."""
        email_clean = email.lower().strip()
        user_id = f"usr_{uuid.uuid4().hex[:8]}"

        # Check existing user
        if self._db is not None:
            user_doc = await self._db.users.find_one({"email": email_clean})
            if user_doc:
                user_id = user_doc["user_id"]
        else:
            for u in _memory_users.values():
                if u.get("email") == email_clean:
                    user_id = u["user_id"]
                    break

        membership = Membership(
            membership_id=f"mem_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            user_email=email_clean,
            organization_id=organization_id,
            role=role,
            joined_at=datetime.utcnow(),
        )

        if self._db is not None:
            await self._db.memberships.insert_one(dict_to_mongo(membership))
        else:
            _memory_memberships[membership.membership_id] = dict_to_mongo(membership)

        await self._audit.log(
            event_type=AuditEventType.MEMBER_INVITED,
            organization_id=organization_id,
            entity_type="membership",
            entity_id=membership.membership_id,
            actor=invited_by,
            actor_id=invited_by,
            message=f"Invited '{email_clean}' as {role.value}.",
            metadata={"email": email_clean, "role": role.value},
        )
        return membership

    async def add_member(
        self,
        org_id: str,
        user_email: str,
        role: UserRole,
        inviter_id: str,
    ) -> Dict[str, Any]:
        """Add an existing user to an organization with a specific role."""
        email_clean = user_email.lower().strip()
        membership = await self.invite_member(org_id, email_clean, role, inviter_id)
        return {"user_id": membership.user_id, "email": email_clean, "role": role.value, "status": "added"}

    async def list_members(self, org_id: str) -> List[Dict[str, Any]]:
        """List all members of an organization."""
        results = []
        if self._db is not None:
            cursor = self._db.memberships.find({"organization_id": org_id})
            members = await cursor.to_list(length=200)
            for m in members:
                user_doc = await self._db.users.find_one({"user_id": m["user_id"]})
                email = user_doc["email"] if user_doc else m.get("user_email", "invited@user.com")
                full_name = user_doc["full_name"] if user_doc else email.split("@")[0]
                results.append({
                    "membership_id": m.get("membership_id"),
                    "user_id": m.get("user_id"),
                    "email": email,
                    "full_name": full_name,
                    "role": m.get("role", "VIEWER"),
                    "joined_at": m.get("joined_at"),
                })
        else:
            for m in _memory_memberships.values():
                if m.get("organization_id") == org_id:
                    user_doc = _memory_users.get(m["user_id"])
                    email = user_doc["email"] if user_doc else m.get("user_email", "invited@user.com")
                    full_name = user_doc["full_name"] if user_doc else email.split("@")[0]
                    results.append({
                        "membership_id": m.get("membership_id"),
                        "user_id": m.get("user_id"),
                        "email": email,
                        "full_name": full_name,
                        "role": m.get("role", "VIEWER"),
                        "joined_at": m.get("joined_at"),
                    })
        return results
