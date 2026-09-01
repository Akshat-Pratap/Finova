"""Finova — Data Ingestion.

Loads financial data from CSV, JSON, synthetic generators, and API responses.
"""
from __future__ import annotations

import io
import json
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class IngestionResult:
    """Result of data ingestion."""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self.source: str = "unknown"
        self.errors: List[str] = []
        self.records_loaded: int = 0

    @property
    def success(self) -> bool:
        return len(self.records) > 0


def ingest_csv(content: bytes, source_name: str = "upload") -> IngestionResult:
    """Load records from CSV bytes."""
    result = IngestionResult()
    result.source = source_name
    try:
        df = pd.read_csv(io.BytesIO(content), dtype=str)
        df = df.where(pd.notnull(df), None)
        result.records = df.to_dict(orient="records")
        result.records_loaded = len(result.records)
        logger.info("Ingested %d records from CSV: %s", result.records_loaded, source_name)
    except Exception as exc:
        result.errors.append(f"CSV parse error: {exc}")
        logger.error("CSV ingestion failed for %s: %s", source_name, exc)
    return result


def ingest_json(content: bytes, source_name: str = "upload") -> IngestionResult:
    """Load records from JSON bytes (list or dict with 'transactions' key)."""
    result = IngestionResult()
    result.source = source_name
    try:
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list):
            result.records = data
        elif isinstance(data, dict):
            # Accept {"transactions": [...]} or just the root dict
            for key in ("transactions", "records", "data"):
                if key in data and isinstance(data[key], list):
                    result.records = data[key]
                    break
            else:
                result.records = [data]
        result.records_loaded = len(result.records)
        logger.info("Ingested %d records from JSON: %s", result.records_loaded, source_name)
    except Exception as exc:
        result.errors.append(f"JSON parse error: {exc}")
        logger.error("JSON ingestion failed for %s: %s", source_name, exc)
    return result


def ingest_synthetic(num_records: int = 250, seed: int = 42) -> Dict[str, IngestionResult]:
    """Generate and ingest a synthetic dataset."""
    from app.services.data_generator import generate_dataset, dataset_to_dicts

    logger.info("Generating synthetic dataset: %d records (seed=%d)", num_records, seed)
    txns, invs, banks, settlements = generate_dataset(num_records=num_records, seed=seed)
    data = dataset_to_dicts(txns, invs, banks, settlements)

    results = {}
    for entity_type, records in data.items():
        r = IngestionResult()
        r.source = "synthetic"
        r.records = records
        r.records_loaded = len(records)
        results[entity_type] = r
        logger.info("Synthetic %s: %d records", entity_type, r.records_loaded)

    return results


def ingest_from_dict_list(records: List[Dict], source: str = "api") -> IngestionResult:
    """Ingest from an already-parsed list of dicts."""
    result = IngestionResult()
    result.source = source
    result.records = records
    result.records_loaded = len(records)
    return result
