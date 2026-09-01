"""Finova — User & Role Model."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    FINANCE_ANALYST = "FINANCE_ANALYST"
    VIEWER = "VIEWER"


class User(BaseModel):
    """User account entity."""

    user_id: str = Field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:12]}")
    email: EmailStr
    hashed_password: str
    full_name: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None

    model_config = {"arbitrary_types_allowed": True}


class UserResponse(BaseModel):
    """Public user response schema."""
    user_id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
