"""Finova — Security utilities."""
from __future__ import annotations

import hashlib
import re
import unicodedata


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filenames to prevent path traversal."""
    # Normalize unicode
    filename = unicodedata.normalize("NFKD", filename)
    # Remove path separators and dangerous characters
    filename = re.sub(r"[^\w\s\-.]", "", filename)
    filename = filename.strip(". ")
    # Truncate
    if len(filename) > 255:
        parts = filename.rsplit(".", 1)
        if len(parts) == 2:
            filename = parts[0][:250] + "." + parts[1]
        else:
            filename = filename[:255]
    return filename or "upload"


ALLOWED_EXTENSIONS = {".csv", ".json"}


def is_allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    import os
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def hash_sensitive(value: str) -> str:
    """One-way hash for sensitive values in logs."""
    return hashlib.sha256(value.encode()).hexdigest()[:12]
