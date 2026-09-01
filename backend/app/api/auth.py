"""Finova — Authentication API Routes."""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

from app.core.database import get_db, is_connected
from app.core.auth_middleware import get_current_user
from app.models.user import User, UserResponse, UserRole
from app.models.organization import Organization
from app.services.auth_service import AuthService
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    org_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post(
    "/register",
    summary="Register a new user and organization",
    status_code=status.HTTP_201_CREATED,
)
async def register(request: RegisterRequest, response: Response):
    """Register a new user account and initialize their primary organization."""
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "WEAK_PASSWORD", "message": "Password must be at least 6 characters long."},
        )

    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    auth_svc = AuthService(db)
    try:
        user, org, access_token, refresh_token = await auth_svc.register(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            org_name=request.org_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "REGISTRATION_FAILED", "message": str(exc)},
        )

    # Set secure HTTP-only cookies
    response.set_cookie(
        key="finova_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production HTTPS
        max_age=86400,
    )
    response.set_cookie(
        key="finova_refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=604800,
    )

    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": "OWNER",
        },
        "organization": dict_to_mongo(org),
    }


@router.post(
    "/login",
    summary="User login",
)
async def login(request: LoginRequest, response: Response):
    """Authenticate with email & password and receive JWT tokens."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    auth_svc = AuthService(db)
    try:
        user, org, access_token, refresh_token, role = await auth_svc.login(
            email=request.email,
            password=request.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": str(exc)},
        )

    response.set_cookie(
        key="finova_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400,
    )
    response.set_cookie(
        key="finova_refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=604800,
    )

    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": role.value if hasattr(role, "value") else str(role),
        },
        "organization": dict_to_mongo(org),
    }


@router.post(
    "/logout",
    summary="User logout",
)
async def logout(response: Response):
    """Clear session cookies."""
    response.delete_cookie("finova_access_token")
    response.delete_cookie("finova_refresh_token")
    return {"success": True, "message": "Logged out successfully."}


@router.get(
    "/me",
    summary="Get current user & organization profile",
)
async def get_me(user: User = Depends(get_current_user)):
    """Retrieve authenticated user details and memberships."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    auth_svc = AuthService(db)
    org, role = await auth_svc.get_primary_org_for_user(user.user_id)

    return {
        "success": True,
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": role.value if hasattr(role, "value") else str(role),
            "created_at": user.created_at,
        },
        "organization": dict_to_mongo(org) if org else None,
    }


@router.post(
    "/refresh",
    summary="Refresh access token",
)
async def refresh_token_endpoint(
    request: RefreshRequest,
    response: Response,
    finova_refresh_token: Optional[str] = Cookie(None),
):
    """Obtain a new access token using a valid refresh token."""
    token = request.refresh_token or finova_refresh_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_REFRESH_TOKEN", "message": "Refresh token required."},
        )

    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    auth_svc = AuthService(db)
    try:
        new_access, new_refresh, payload = await auth_svc.refresh_tokens(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": str(exc)},
        )

    response.set_cookie(
        key="finova_access_token",
        value=new_access,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400,
    )
    response.set_cookie(
        key="finova_refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=604800,
    )

    return {
        "success": True,
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post(
    "/forgot-password",
    summary="Request password reset",
)
async def forgot_password(request: ForgotPasswordRequest):
    """Initiate password reset process."""
    return {
        "success": True,
        "message": f"If an account exists for {request.email}, password reset instructions have been dispatched.",
    }
