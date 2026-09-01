"""Finova — Authentication Service.

Handles registration, login, JWT token lifecycle, and password management.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.core.database import get_db, is_connected
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User, UserRole, UserResponse
from app.models.organization import Organization, OrgSettings
from app.models.membership import Membership
from app.models.audit_log import AuditEventType
from app.services.audit_logger import AuditLogger
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)

# In-memory storage for test/demo mode when MongoDB is not connected
_memory_users: Dict[str, dict] = {}
_memory_orgs: Dict[str, dict] = {}
_memory_memberships: Dict[str, dict] = {}


class AuthService:
    """Authentication and identity operations."""

    def __init__(self, db=None):
        self._db = db

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        org_name: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> Tuple[User, Organization, str, str]:
        """
        Register a new user account, bootstrap primary organization with OWNER role,
        and generate access + refresh JWT tokens.
        """
        email_clean = email.lower().strip()
        existing = await self.get_user_by_email(email_clean)
        if existing:
            raise ValueError(f"An account with email '{email_clean}' already exists.")

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        user = User(
            user_id=user_id,
            email=email_clean,
            hashed_password=hash_password(password),
            full_name=full_name.strip(),
            created_at=datetime.utcnow(),
        )

        # Create primary organization
        effective_org_name = organization_name or org_name
        org_title = (effective_org_name or f"{user.full_name}'s Organization").strip()
        slug = f"{org_title.lower().replace(' ', '-')[:30]}-{uuid.uuid4().hex[:4]}"
        org = Organization(
            organization_id=f"org_{uuid.uuid4().hex[:12]}",
            name=org_title,
            slug=slug,
            owner_user_id=user.user_id,
            created_at=datetime.utcnow(),
        )

        # Create Owner membership
        membership = Membership(
            membership_id=f"mem_{uuid.uuid4().hex[:12]}",
            user_id=user.user_id,
            organization_id=org.organization_id,
            role=UserRole.OWNER,
            joined_at=datetime.utcnow(),
        )

        # Persist
        if self._db is not None:
            await self._db.users.insert_one(dict_to_mongo(user))
            await self._db.organizations.insert_one(dict_to_mongo(org))
            await self._db.memberships.insert_one(dict_to_mongo(membership))
        else:
            _memory_users[user.user_id] = dict_to_mongo(user)
            _memory_orgs[org.organization_id] = dict_to_mongo(org)
            _memory_memberships[membership.membership_id] = dict_to_mongo(membership)

        # Audit log
        audit = AuditLogger(self._db)
        await audit.log(
            event_type=AuditEventType.USER_REGISTERED,
            organization_id=org.organization_id,
            entity_type="user",
            entity_id=user.user_id,
            actor=user.email,
            actor_id=user.user_id,
            message=f"User {user.email} registered. Organization {org.name} created.",
        )

        token_payload = {
            "sub": user.user_id,
            "email": user.email,
            "org_id": org.organization_id,
            "role": membership.role.value,
        }
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)

        return user, org, access_token, refresh_token

    async def login(
        self,
        email: str,
        password: str,
    ) -> Tuple[User, Organization, str, str, UserRole]:
        """
        Authenticate user and return (User, primary Organization, access_token, refresh_token, Role).
        """
        email_clean = email.lower().strip()
        user_doc = None

        if self._db is not None:
            user_doc = await self._db.users.find_one({"email": email_clean})
        else:
            for u in _memory_users.values():
                if u.get("email") == email_clean:
                    user_doc = u
                    break

        if not user_doc or not verify_password(password, user_doc.get("hashed_password", "")):
            raise ValueError("Invalid email or password.")

        user_doc.pop("_id", None)
        user = User(**user_doc)

        # Find primary organization & membership
        org, role = await self.get_primary_org_for_user(user.user_id)
        if not org:
            # Bootstrap an organization if missing
            org = Organization(
                organization_id=f"org_{uuid.uuid4().hex[:12]}",
                name=f"{user.full_name}'s Organization",
                slug=f"org-{uuid.uuid4().hex[:6]}",
                owner_user_id=user.user_id,
            )
            role = UserRole.OWNER
            mem = Membership(
                user_id=user.user_id,
                organization_id=org.organization_id,
                role=role,
            )
            if self._db is not None:
                await self._db.organizations.insert_one(dict_to_mongo(org))
                await self._db.memberships.insert_one(dict_to_mongo(mem))
            else:
                _memory_orgs[org.organization_id] = dict_to_mongo(org)
                _memory_memberships[mem.membership_id] = dict_to_mongo(mem)

        # Update last login
        now = datetime.utcnow()
        if self._db is not None:
            await self._db.users.update_one(
                {"user_id": user.user_id},
                {"$set": {"last_login_at": now}},
            )

        token_payload = {
            "sub": user.user_id,
            "email": user.email,
            "org_id": org.organization_id,
            "role": role.value if hasattr(role, "value") else str(role),
        }
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)

        audit = AuditLogger(self._db)
        await audit.log(
            event_type=AuditEventType.LOGIN,
            organization_id=org.organization_id,
            entity_type="user",
            entity_id=user.user_id,
            actor=user.email,
            actor_id=user.user_id,
            message=f"User {user.email} logged in successfully.",
        )

        return user, org, access_token, refresh_token, role

    async def get_user_by_email(self, email: str) -> Optional[User]:
        email_clean = email.lower().strip()
        if self._db is not None:
            doc = await self._db.users.find_one({"email": email_clean})
            if doc:
                doc.pop("_id", None)
                return User(**doc)
            return None
        for u in _memory_users.values():
            if u.get("email") == email_clean:
                data = u.copy()
                data.pop("_id", None)
                return User(**data)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        if self._db is not None:
            doc = await self._db.users.find_one({"user_id": user_id})
            if doc:
                doc.pop("_id", None)
                return User(**doc)
            return None
        if user_id in _memory_users:
            data = _memory_users[user_id].copy()
            data.pop("_id", None)
            return User(**data)
        return None

    async def get_primary_org_for_user(self, user_id: str) -> Tuple[Optional[Organization], UserRole]:
        """Get the primary organization and role for a user."""
        mem_doc = None
        if self._db is not None:
            mem_doc = await self._db.memberships.find_one({"user_id": user_id})
        else:
            for m in _memory_memberships.values():
                if m.get("user_id") == user_id:
                    mem_doc = m
                    break

        if not mem_doc:
            return None, UserRole.VIEWER

        org_id = mem_doc.get("organization_id")
        role = UserRole(mem_doc.get("role", "VIEWER"))

        org = await self.get_org_by_id(org_id)
        return org, role

    async def get_org_by_id(self, org_id: str) -> Optional[Organization]:
        if self._db is not None:
            doc = await self._db.organizations.find_one({"organization_id": org_id})
            if doc:
                doc.pop("_id", None)
                return Organization(**doc)
            return None
        if org_id in _memory_orgs:
            data = _memory_orgs[org_id].copy()
            data.pop("_id", None)
            return Organization(**data)
        return None

    async def refresh_tokens(self, refresh_token: str) -> Tuple[str, str, Dict[str, Any]]:
        """Validate refresh token and issue new token pair."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid or expired refresh token.")

        user_id = payload.get("sub")
        user = await self.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or account deactivated.")

        org_id = payload.get("org_id")
        role = payload.get("role", "VIEWER")

        new_payload = {
            "sub": user.user_id,
            "email": user.email,
            "org_id": org_id,
            "role": role,
        }
        new_access = create_access_token(new_payload)
        new_refresh = create_refresh_token(new_payload)
        return new_access, new_refresh, new_payload
