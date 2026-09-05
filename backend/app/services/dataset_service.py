"""Finova — Dataset Service.

Manages uploaded files, column mapping, validation previews, and dataset lifecycles.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.models.dataset import (
    Dataset, DatasetStatus, DatasetType,
    infer_dataset_type, get_compatible_types, get_validation_profile
)
from app.models.audit_log import AuditEventType
from app.services.audit_logger import AuditLogger
from app.services.data_engine.column_mapper import detect_column_mapping, apply_column_mapping
from app.services.data_engine.ingestion import ingest_csv, ingest_json, IngestionResult
from app.services.data_engine.cleaner import clean_transactions
from app.services.data_engine.normalizer import normalize_transactions
from app.services.data_engine.validator import validate_transactions
from app.services.data_engine.dataset_validator import validate_records_for_type
from app.services.memory_store import memory_datasets, memory_dataset_records
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)


async def _persist_records_background(
    db: Any,
    dataset_id: str,
    organization_id: str,
    records: List[Dict[str, Any]],
) -> None:
    """Persist large record sets to MongoDB asynchronously in chunks."""
    try:
        chunk_size = 2000
        for i in range(0, len(records), chunk_size):
            chunk = records[i : i + chunk_size]
            await db.dataset_records.insert_many(
                [
                    {
                        "dataset_id": dataset_id,
                        "organization_id": organization_id,
                        "record": r,
                    }
                    for r in chunk
                ],
                ordered=False,
            )
        logger.info("Successfully persisted %d records for dataset %s to MongoDB", len(records), dataset_id)
    except Exception as exc:
        logger.warning(
            "Background dataset_records persistence failed for %s: %s (memory fallback active)",
            dataset_id,
            exc,
        )


class DatasetService:
    """Dataset management operations."""

    def __init__(self, db=None):
        self._db = db
        self._audit = AuditLogger(db)

    async def upload_dataset(
        self,
        content: bytes,
        filename: str,
        organization_id: str,
        user_id: Optional[str] = None,
    ) -> Tuple[Dataset, Dict[str, str], List[Dict[str, Any]]]:
        """
        Ingest uploaded CSV/JSON, auto-detect column mappings,
        save dataset in UPLOADED status, and return (Dataset, detected_mappings, sample_rows).
        """
        filename_lower = filename.lower()
        if filename_lower.endswith(".json"):
            ingestion = ingest_json(content, source_name=filename)
        else:
            ingestion = ingest_csv(content, source_name=filename)

        if not ingestion.success or not ingestion.records:
            err_msg = "; ".join(ingestion.errors) if ingestion.errors else "No valid records parsed from file"
            raise ValueError(f"Failed to parse dataset: {err_msg}")

        sample_records = ingestion.records[:5]
        columns = list(sample_records[0].keys()) if sample_records else []
        auto_mapping = detect_column_mapping(columns)
        # Infer dataset type from auto-mapping and raw columns (never filename)
        inferred_type = infer_dataset_type(auto_mapping, raw_columns=columns, raw_sample=sample_records)

        dataset = Dataset(
            dataset_id=f"ds_{uuid.uuid4().hex[:12]}",
            organization_id=organization_id,
            filename=filename,
            source_type="json" if filename_lower.endswith(".json") else "csv",
            dataset_type=inferred_type,
            record_count=len(ingestion.records),
            column_mapping=auto_mapping,
            canonical_fields=list(auto_mapping.values()),
            required_fields=get_validation_profile(inferred_type).get("required", []),
            uploaded_by=user_id,
            uploaded_at=datetime.utcnow(),
            processing_status=DatasetStatus.UPLOADED,
            raw_sample=sample_records,
        )

        # Always cache in-memory for immediate fast path
        memory_datasets[dataset.dataset_id] = dict_to_mongo(dataset)
        memory_dataset_records[dataset.dataset_id] = ingestion.records

        if self._db is not None:
            try:
                await self._db.datasets.insert_one(dict_to_mongo(dataset))
                # Persist full records asynchronously so HTTP upload returns immediately
                if ingestion.records:
                    asyncio.create_task(
                        _persist_records_background(
                            self._db, dataset.dataset_id, organization_id, ingestion.records
                        )
                    )
            except Exception as exc:
                logger.warning(
                    "Could not persist dataset metadata to MongoDB (%s). Using memory cache fallback.", exc
                )

        await self._audit.log(
            event_type=AuditEventType.DATASET_UPLOADED,
            organization_id=organization_id,
            entity_type="dataset",
            entity_id=dataset.dataset_id,
            actor=user_id or "user",
            actor_id=user_id,
            message=f"Uploaded dataset '{filename}' ({len(ingestion.records)} records detected).",
            metadata={"record_count": len(ingestion.records), "filename": filename},
        )

        return dataset, auto_mapping, sample_records

    async def get_dataset(self, dataset_id: str, organization_id: Optional[str] = None) -> Optional[Dataset]:
        """Fetch dataset document."""
        query: Dict[str, Any] = {"dataset_id": dataset_id}
        if organization_id:
            query["organization_id"] = organization_id

        if self._db is not None:
            doc = await self._db.datasets.find_one(query)
            if doc:
                doc.pop("_id", None)
                return Dataset(**doc)
            return None
        if dataset_id in memory_datasets:
            d = memory_datasets[dataset_id].copy()
            d.pop("_id", None)
            if organization_id and d.get("organization_id") != organization_id:
                return None
            return Dataset(**d)
        return None

    async def list_datasets(self, organization_id: str, limit: int = 50, skip: int = 0) -> Tuple[List[Dataset], int]:
        """List datasets for an organization."""
        if self._db is not None:
            cursor = self._db.datasets.find({"organization_id": organization_id}).sort("uploaded_at", -1).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            total = await self._db.datasets.count_documents({"organization_id": organization_id})
            results = []
            for d in docs:
                d.pop("_id", None)
                results.append(Dataset(**d))
            return results, total

        all_ds = [Dataset(**d.copy()) for d in memory_datasets.values() if d.get("organization_id") == organization_id]
        all_ds.sort(key=lambda x: x.uploaded_at, reverse=True)
        return all_ds[skip:skip+limit], len(all_ds)

    async def validate_dataset(
        self,
        dataset_id: str,
        organization_id: str,
        custom_mapping: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply column mapping, clean & normalize records, run validation checks,
        and update dataset with valid/invalid counts and error reports.
        Generic: supports BANK, INVOICE, PAYMENT, SETTLEMENT, LEDGER, GENERIC.
        """
        dataset = await self.get_dataset(dataset_id, organization_id)
        if not dataset:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        raw_records = memory_dataset_records.get(dataset_id, [])
        if not raw_records:
            # Fallback to MongoDB if not in memory
            raw_records = await self.get_dataset_records(dataset_id)
        if not raw_records and dataset.raw_sample:
            raw_records = dataset.raw_sample

        mapping = custom_mapping or dataset.column_mapping
        # Persist mapping immediately so inference uses the correct mapping
        if custom_mapping:
            dataset.column_mapping = mapping

        # Re-infer type from the (possibly custom) mapping
        columns_for_inference = list(raw_records[0].keys()) if raw_records else list(mapping.keys())
        inferred_type = infer_dataset_type(mapping, raw_columns=columns_for_inference, raw_sample=raw_records)
        # Allow explicit dataset_type override via custom_mapping metadata? For now inferred is authoritative
        dataset.dataset_type = inferred_type
        dataset.canonical_fields = list(mapping.values())
        dataset.required_fields = get_validation_profile(inferred_type).get("required", [])

        mapped_records = apply_column_mapping(raw_records, mapping)

        # Generic type-aware validation (does not require transaction_id for invoices)
        valid_records, report = validate_records_for_type(
            mapped_records, dataset_type=inferred_type
        )

        # Also run legacy duplicate-aware cleaning for transaction-type to enrich diagnostics, but don't double-count
        # For generic types, the new validator already handled duplicates

        dataset.record_count = len(raw_records)
        dataset.valid_count = report.records_valid
        dataset.invalid_count = report.records_invalid
        dataset.duplicate_count = report.duplicates_detected
        dataset.validation_errors = report.validation_errors[:50]
        dataset.validation_diagnostics = report.diagnostics[:20]
        dataset.validated_at = datetime.utcnow()
        # Status lifecycle: VALIDATED if any valid, else FAILED
        if report.records_valid > 0:
            dataset.processing_status = DatasetStatus.VALIDATED
        else:
            dataset.processing_status = DatasetStatus.FAILED

        update_doc = {
            "column_mapping": mapping,
            "dataset_type": dataset.dataset_type,
            "canonical_fields": dataset.canonical_fields,
            "required_fields": dataset.required_fields,
            "valid_count": dataset.valid_count,
            "invalid_count": dataset.invalid_count,
            "duplicate_count": dataset.duplicate_count,
            "validation_errors": dataset.validation_errors,
            "validation_diagnostics": dataset.validation_diagnostics,
            "processing_status": dataset.processing_status.value,
            "validated_at": dataset.validated_at,
        }

        if self._db is not None:
            await self._db.datasets.update_one(
                {"dataset_id": dataset_id},
                {"$set": update_doc},
            )
        else:
            memory_datasets[dataset_id].update({k: v.value if hasattr(v, 'value') else v for k, v in update_doc.items()})

        await self._audit.log(
            event_type=AuditEventType.DATASET_VALIDATED,
            organization_id=organization_id,
            entity_type="dataset",
            entity_id=dataset.dataset_id,
            actor=user_id or "user",
            actor_id=user_id,
            message=f"Dataset '{dataset.filename}' [{inferred_type}] validated: {report.records_valid} valid, {report.records_invalid} invalid.",
            metadata=report.to_dict(),
        )

        return {
            "dataset_id": dataset.dataset_id,
            "filename": dataset.filename,
            "dataset_type": dataset.dataset_type,
            "status": dataset.processing_status.value,
            "record_count": dataset.record_count,
            "valid_count": dataset.valid_count,
            "invalid_count": dataset.invalid_count,
            "duplicate_count": dataset.duplicate_count,
            "validation_errors": report.validation_errors,
            "validation_diagnostics": report.diagnostics,
            "mapping_applied": mapping,
            "ready_for_processing": report.records_valid > 0,
            "canonical_fields": dataset.canonical_fields,
        }

    async def find_compatible_counterparts(
        self,
        source_dataset_id: str,
        organization_id: str,
        limit: int = 10,
    ) -> List[Dataset]:
        """Find validated compatible counterpart datasets for a source dataset."""
        source = await self.get_dataset(source_dataset_id, organization_id)
        if not source:
            raise ValueError(f"Source dataset '{source_dataset_id}' not found.")

        compatible_types = get_compatible_types(source.dataset_type)
        # Also include UNKNOWN as compatible fallback
        compatible_list = list(compatible_types)

        # Query for compatible datasets — include UPLOADED so we can auto-validate on demand
        # Validated datasets are preferred, but UPLOADED with data can be auto-validated when used as counterpart
        query = {
            "organization_id": organization_id,
            "dataset_id": {"$ne": source_dataset_id},
            "dataset_type": {"$in": compatible_list},
        }

        if self._db is not None:
            cursor = self._db.datasets.find(query).sort("validated_at", -1).limit(limit * 3)
            docs = await cursor.to_list(length=limit * 3)
            results = []
            for d in docs:
                d.pop("_id", None)
                if d.get("organization_id") != organization_id:
                    continue
                # Allow UPLOADED (can be auto-validated) or VALIDATED with data
                status = d.get("processing_status")
                if status == DatasetStatus.VALIDATED.value and d.get("valid_count", 0) <= 0:
                    continue
                if status not in (DatasetStatus.UPLOADED.value, DatasetStatus.VALIDATED.value, DatasetStatus.READY_FOR_RECONCILIATION.value, DatasetStatus.COMPLETED.value):
                    continue
                if d.get("record_count", 0) <= 0 and d.get("valid_count", 0) <= 0:
                    continue
                results.append(Dataset(**d))
                if len(results) >= limit:
                    break
            # Prefer VALIDATED first, then UPLOADED
            results.sort(key=lambda x: (0 if x.processing_status == DatasetStatus.VALIDATED else 1, -(x.validated_at.timestamp() if x.validated_at else x.uploaded_at.timestamp())))
            return results[:limit]
        else:
            # Memory fallback — include UPLOADED so we can auto-validate on demand
            candidates = []
            for d in memory_datasets.values():
                if d.get("organization_id") != organization_id:
                    continue
                if d.get("dataset_id") == source_dataset_id:
                    continue
                if d.get("dataset_type") not in compatible_list:
                    continue
                status = d.get("processing_status")
                if status not in (DatasetStatus.UPLOADED.value, DatasetStatus.VALIDATED.value, DatasetStatus.READY_FOR_RECONCILIATION.value, DatasetStatus.COMPLETED.value):
                    continue
                if d.get("record_count", 0) <= 0 and d.get("valid_count", 0) <= 0:
                    continue
                d_copy = d.copy()
                d_copy.pop("_id", None)
                candidates.append(Dataset(**d_copy))
            # Prefer VALIDATED first
            candidates.sort(key=lambda x: (0 if x.processing_status == DatasetStatus.VALIDATED else 1, -(x.validated_at.timestamp() if x.validated_at else x.uploaded_at.timestamp())))
            return candidates[:limit]

    async def get_dataset_records(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Retrieve stored raw records for a dataset.

        Checks the in-memory cache first (fast path for same-process requests),
        then falls back to MongoDB so records survive worker restarts.
        """
        in_memory = memory_dataset_records.get(dataset_id, [])
        if in_memory:
            return in_memory
        if self._db is not None:
            cursor = self._db.dataset_records.find(
                {"dataset_id": dataset_id},
                {"_id": 0, "record": 1},
            )
            docs = await cursor.to_list(length=100_000)
            records = [d["record"] for d in docs]
            # Repopulate cache for subsequent same-process calls
            if records:
                memory_dataset_records[dataset_id] = records
            return records
        return []

    async def delete_dataset(
        self,
        dataset_id: str,
        organization_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Permanently delete a dataset and all its stored records from MongoDB Atlas & memory."""
        dataset = await self.get_dataset(dataset_id, organization_id)
        if not dataset:
            return False

        # Clear from memory
        memory_datasets.pop(dataset_id, None)
        memory_dataset_records.pop(dataset_id, None)

        # Delete from MongoDB Atlas
        if self._db is not None:
            try:
                await self._db.datasets.delete_one({"dataset_id": dataset_id, "organization_id": organization_id})
                await self._db.dataset_records.delete_many({"dataset_id": dataset_id, "organization_id": organization_id})
            except Exception as exc:
                logger.error("Failed to delete dataset %s from MongoDB: %s", dataset_id, exc)
                raise

        await self._audit.log(
            event_type=AuditEventType.DATASET_DELETED,
            organization_id=organization_id,
            entity_type="dataset",
            entity_id=dataset_id,
            actor=user_id or "user",
            actor_id=user_id,
            message=f"Deleted dataset '{dataset.filename}' ({dataset.record_count} records purged).",
            metadata={"dataset_id": dataset_id, "filename": dataset.filename},
        )

        return True
