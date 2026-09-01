"""Finova — Financial Report Generator.

Generates CSV and JSON financial exports for reconciliation, exceptions, audit logs, and transactions.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.models.report import ReportType, ReportFormat
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)


def generate_csv_report(records: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> str:
    """Serialize records into clean CSV string."""
    if not records:
        return ""

    if not fieldnames:
        # Collect all unique fieldnames
        keys = []
        for r in records:
            for k in r.keys():
                if k not in keys and not k.startswith("_"):
                    keys.append(k)
        fieldnames = keys

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for row in records:
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, (datetime,)):
                clean_row[k] = v.isoformat()
            elif isinstance(v, (Decimal,)):
                clean_row[k] = str(v)
            elif isinstance(v, (dict, list)):
                clean_row[k] = json.dumps(v, default=str)
            else:
                clean_row[k] = v
        writer.writerow(clean_row)

    return output.getvalue()


def generate_json_report(records: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> str:
    """Serialize records into structured JSON export string."""
    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "record_count": len(records),
        "metadata": metadata or {},
        "records": records,
    }
    return json.dumps(payload, indent=2, default=str)
