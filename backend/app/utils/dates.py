"""Finova — Date utilities."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def days_between(d1: datetime, d2: datetime) -> int:
    """Absolute number of days between two datetimes."""
    return abs((d1 - d2).days)


def parse_date(value: str) -> Optional[datetime]:
    """Try common date formats."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None
