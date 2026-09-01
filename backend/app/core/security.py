"""Finova — Security utilities."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a signed JWT refresh token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh",
    })
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.PyJWTError:
        return None


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filenames to prevent path traversal."""
    filename = unicodedata.normalize("NFKD", filename)
    filename = re.sub(r"[^\w\s\-.]", "", filename)
    filename = filename.strip(". ")
    if len(filename) > 255:
        parts = filename.rsplit(".", 1)
        if len(parts) == 2:
            filename = parts[0][:250] + "." + parts[1]
        else:
            filename = filename[:255]
    return filename or "upload"


ALLOWED_EXTENSIONS = {".csv", ".json", ".txt"}


def is_allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    import os
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def hash_sensitive(value: str) -> str:
    """One-way hash for sensitive values in logs."""
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def mask_secret(secret: str) -> str:
    """Mask a secret key for UI display (e.g., rzp_test_***1234)."""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "****"
    return secret[:6] + "..." + secret[-4:]

