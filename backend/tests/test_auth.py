"""Finova — Authentication & Password Security Tests."""
from __future__ import annotations

import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.services.auth_service import AuthService
from app.models.user import UserRole


def test_password_hashing():
    pwd = "SecureFinovaPassword2026!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_lifecycle():
    user_id = "usr_test123"
    token = create_access_token({"sub": user_id, "role": "OWNER"})
    decoded = decode_token(token)
    assert decoded["sub"] == user_id
    assert decoded["role"] == "OWNER"
    assert "exp" in decoded


@pytest.mark.asyncio
async def test_auth_service_registration_and_login():
    auth_svc = AuthService(db=None)

    # 1. Register new user
    user, org, access_token, refresh_token = await auth_svc.register(
        email="cfo@acmecorp.com",
        password="CFOSecretPassword123!",
        full_name="Jane Doe",
        organization_name="Acme Corp Financials",
    )

    assert user.email == "cfo@acmecorp.com"
    assert user.full_name == "Jane Doe"
    assert org.name == "Acme Corp Financials"
    assert access_token is not None
    assert refresh_token is not None

    # 2. Login
    logged_user, user_org, access_token, refresh_token, role = await auth_svc.login(
        email="cfo@acmecorp.com",
        password="CFOSecretPassword123!",
    )
    assert logged_user.user_id == user.user_id
    assert user_org.name == "Acme Corp Financials"
    assert access_token is not None
    assert refresh_token is not None
    assert role == UserRole.OWNER

    # 3. Invalid password rejects
    with pytest.raises(ValueError, match="Invalid email or password"):
        await auth_svc.login(email="cfo@acmecorp.com", password="WrongPassword!")
