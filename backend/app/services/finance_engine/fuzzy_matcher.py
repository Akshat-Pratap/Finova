"""Finova — Fuzzy Matcher.

Uses RapidFuzz for text similarity matching of customer names, references,
and descriptions. Only used when deterministic matching fails.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from rapidfuzz import fuzz


def normalize_for_fuzzy(s: str) -> str:
    """Normalize string for fuzzy comparison."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.lower().strip()
    # Remove common noise
    s = re.sub(r"[\s\-_/]", "", s)
    return s


def reference_similarity(ref1: Optional[str], ref2: Optional[str]) -> float:
    """
    Compute fuzzy similarity between two reference strings.

    Returns 0.0–1.0.
    Examples:
        "INV-8291" vs "INV8291"  → ~0.95
        "INV-8291" vs "INV-1921" → ~0.50
    """
    if not ref1 or not ref2:
        return 0.0

    n1 = normalize_for_fuzzy(ref1)
    n2 = normalize_for_fuzzy(ref2)

    if not n1 or not n2:
        return 0.0

    # Exact match after normalization
    if n1 == n2:
        return 1.0

    # Ratio and partial ratio
    ratio = fuzz.ratio(n1, n2) / 100.0
    token_sort = fuzz.token_sort_ratio(n1, n2) / 100.0
    partial = fuzz.partial_ratio(n1, n2) / 100.0

    score = max(ratio, token_sort) * 0.7 + partial * 0.3

    # Penalize very short strings — too much false positive risk
    min_len = min(len(n1), len(n2))
    if min_len < 4:
        score *= 0.5

    return round(min(score, 1.0), 4)


def customer_name_similarity(name1: Optional[str], name2: Optional[str]) -> float:
    """Fuzzy comparison of customer names."""
    if not name1 or not name2:
        return 0.0

    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    if n1 == n2:
        return 1.0

    token_sort = fuzz.token_sort_ratio(n1, n2) / 100.0
    token_set = fuzz.token_set_ratio(n1, n2) / 100.0

    return round(max(token_sort, token_set), 4)


def description_similarity(desc1: Optional[str], desc2: Optional[str]) -> float:
    """Fuzzy comparison of transaction descriptions."""
    if not desc1 or not desc2:
        return 0.0

    n1 = desc1.lower().strip()
    n2 = desc2.lower().strip()

    if n1 == n2:
        return 1.0

    # Use partial ratio — descriptions can be subsets of each other
    return round(fuzz.partial_ratio(n1, n2) / 100.0, 4)


REFERENCE_FUZZY_THRESHOLD = 0.80  # Min score to consider a fuzzy reference match
CUSTOMER_FUZZY_THRESHOLD = 0.85   # Min score to consider a customer name match
