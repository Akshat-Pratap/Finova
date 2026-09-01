"""Finova — General helpers."""
from __future__ import annotations

import re
import unicodedata
import uuid
from typing import Any, Dict


def generate_id(prefix: str = "") -> str:
    """Generate a short unique ID."""
    uid = uuid.uuid4().hex[:8].upper()
    return f"{prefix}{uid}" if prefix else uid


def normalize_string(s: str) -> str:
    """Normalize a string for comparison: lowercase, strip, remove extra spaces."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_reference(ref: str) -> str:
    """Normalize reference IDs by removing hyphens, spaces, and lowercasing."""
    if not ref:
        return ""
    return re.sub(r"[\s\-_]", "", ref.lower())


def dict_to_mongo(obj: Any) -> Dict:
    """Convert Pydantic model to MongoDB-safe dict."""
    if hasattr(obj, "model_dump"):
        d = obj.model_dump()
    elif isinstance(obj, dict):
        d = obj
    else:
        d = dict(obj)
    # Convert Decimal to float for MongoDB
    return _convert_decimals(d)


def _convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal to float."""
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimals(i) for i in obj]
    return obj
