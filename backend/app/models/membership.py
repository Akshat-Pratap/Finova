"""Finova — Membership Model (User <-> Organization RBAC)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.user import UserRole


class Membership(BaseModel):
    """Associates a User with an Organization with a designated Role."""

    membership_id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    user_id: str
    user_email: Optional[str] = None
    organization_id: str
    role: UserRole = UserRole.FINANCE_ANALYST
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
