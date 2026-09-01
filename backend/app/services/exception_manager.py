"""Finova — Exception Manager.

Creates, tracks, assigns, investigates, and resolves financial exceptions.
Supports user comments, audited non-destructive adjustments, and status workflows.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.models.exception import (
    FinovaException, ExceptionType, ExceptionSeverity, ExceptionStatus, ExceptionNote, ExceptionAdjustment
)
from app.models.reconciliation import ReconciliationResult, ReconciliationStatus
from app.models.audit_log import AuditEventType
from app.services.audit_logger import AuditLogger
from app.services.memory_store import memory_exceptions, memory_notes, memory_adjustments
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)


class ExceptionManager:
    """Manages financial exceptions throughout their complete lifecycle."""

    def __init__(self, db=None):
        self._db = db
        self._audit = AuditLogger(db)

    async def create_from_result(
        self,
        result: ReconciliationResult,
        processing_run_id: str,
        organization_id: str = "org_default",
    ) -> Optional[FinovaException]:
        """
        Create an exception for a reconciliation result that needs attention.
        Only creates exceptions for non-MATCHED statuses.
        """
        if result.status == ReconciliationStatus.MATCHED:
            return None

        exc_type, severity, description = _classify_exception(result)

        exception = FinovaException(
            exception_id=f"EX-{uuid.uuid4().hex[:8].upper()}",
            processing_run_id=processing_run_id,
            organization_id=organization_id,
            transaction_id=result.transaction_id,
            result_id=result.result_id,
            type=exc_type,
            severity=severity,
            description=description,
            expected_value=result.expected_amount,
            actual_value=result.actual_amount,
            difference=result.difference,
        )

        await self._persist(exception)
        logger.info("Exception created: %s | type=%s | txn=%s", exception.exception_id, exc_type.value, result.transaction_id)
        return exception

    async def update_with_ai_result(
        self,
        exception: FinovaException,
        investigation,
    ) -> FinovaException:
        """Update exception with AI investigation results."""
        exception.ai_finding = investigation.finding
        exception.ai_confidence = investigation.confidence
        exception.ai_recommendation = investigation.recommendation
        exception.ai_evidence = investigation.evidence
        exception.ai_requires_manual_review = investigation.requires_manual_review

        if not investigation.requires_manual_review and investigation.confidence >= 0.80:
            exception.status = ExceptionStatus.UNDER_REVIEW

        await self._update(exception)
        return exception

    async def assign(
        self,
        exception_id: str,
        assignee_email: str,
        actor: str = "system",
        organization_id: str = "org_default",
    ) -> Optional[FinovaException]:
        """Assign an exception to a finance officer."""
        exception = await self.get(exception_id, organization_id)
        if not exception:
            return None

        exception.assigned_to = assignee_email
        if exception.status == ExceptionStatus.OPEN:
            exception.status = ExceptionStatus.UNDER_REVIEW

        await self._update(exception)

        await self._audit.log(
            event_type=AuditEventType.EXCEPTION_ASSIGNED,
            organization_id=organization_id,
            entity_type="exception",
            entity_id=exception_id,
            actor=actor,
            message=f"Exception {exception_id} assigned to {assignee_email}.",
        )
        return exception

    async def add_note(
        self,
        exception_id: str,
        content: str,
        author: str,
        author_id: Optional[str] = None,
        organization_id: str = "org_default",
    ) -> ExceptionNote:
        """Add a comment/note to an exception thread without altering raw financial evidence."""
        note = ExceptionNote(
            note_id=f"not_{uuid.uuid4().hex[:8]}",
            exception_id=exception_id,
            organization_id=organization_id,
            author=author,
            author_id=author_id,
            content=content.strip(),
            created_at=datetime.utcnow(),
        )

        memory_notes.append(dict_to_mongo(note))

        if self._db is not None:
            try:
                await self._db.exception_notes.insert_one(dict_to_mongo(note))
            except Exception as exc:
                logger.error("Failed to persist exception note: %s", exc)

        return note

    async def list_notes(self, exception_id: str, organization_id: str = "org_default") -> List[ExceptionNote]:
        """List all comments on an exception."""
        if self._db is not None:
            cursor = self._db.exception_notes.find({"exception_id": exception_id}).sort("created_at", 1)
            docs = await cursor.to_list(length=100)
            return [ExceptionNote(**d) for d in docs]

        notes = [ExceptionNote(**n) for n in memory_notes if n.get("exception_id") == exception_id]
        notes.sort(key=lambda x: x.created_at)
        return notes

    async def record_adjustment(
        self,
        exception_id: str,
        amount: Decimal,
        currency: str,
        reason: str,
        approved_by: str,
        organization_id: str = "org_default",
    ) -> ExceptionAdjustment:
        """
        Record a financial adjustment for an exception.
        Original transaction values remain intact for data immutability.
        """
        adjustment = ExceptionAdjustment(
            adjustment_id=f"adj_{uuid.uuid4().hex[:8]}",
            exception_id=exception_id,
            organization_id=organization_id,
            amount=amount,
            currency=currency,
            reason=reason.strip(),
            approved_by=approved_by,
            created_at=datetime.utcnow(),
        )

        memory_adjustments.append(dict_to_mongo(adjustment))

        if self._db is not None:
            try:
                await self._db.exception_adjustments.insert_one(dict_to_mongo(adjustment))
            except Exception as exc:
                logger.error("Failed to persist adjustment: %s", exc)

        await self._audit.log(
            event_type=AuditEventType.ADJUSTMENT_RECORDED,
            organization_id=organization_id,
            entity_type="exception",
            entity_id=exception_id,
            actor=approved_by,
            message=f"Financial adjustment of {currency} {amount} recorded for {exception_id}: {reason}",
            metadata={"amount": float(amount), "currency": currency, "reason": reason},
        )

        return adjustment

    async def resolve(
        self,
        exception_id: str,
        resolution: str,
        actor: str = "finance_officer",
        notes: Optional[str] = None,
        organization_id: str = "org_default",
    ) -> Optional[FinovaException]:
        """Resolve an exception."""
        exception = await self.get(exception_id, organization_id)
        if not exception:
            return None

        exception.status = ExceptionStatus.RESOLVED
        exception.resolution = resolution
        exception.resolved_by = actor
        exception.resolved_at = datetime.utcnow()
        exception.notes = notes
        await self._update(exception)

        await self._audit.log(
            event_type=AuditEventType.EXCEPTION_RESOLVED,
            organization_id=organization_id,
            entity_type="exception",
            entity_id=exception_id,
            actor=actor,
            message=f"Exception resolved: {resolution}",
        )
        return exception

    async def reject(
        self,
        exception_id: str,
        actor: str = "finance_officer",
        notes: Optional[str] = None,
        organization_id: str = "org_default",
    ) -> Optional[FinovaException]:
        """Reject an exception (mark as confirmed discrepancy)."""
        exception = await self.get(exception_id, organization_id)
        if not exception:
            return None

        exception.status = ExceptionStatus.REJECTED
        exception.resolution = "REJECTED — discrepancy confirmed as legitimate"
        exception.resolved_by = actor
        exception.resolved_at = datetime.utcnow()
        exception.notes = notes
        await self._update(exception)

        await self._audit.log(
            event_type=AuditEventType.EXCEPTION_REJECTED,
            organization_id=organization_id,
            entity_type="exception",
            entity_id=exception_id,
            actor=actor,
            message="Exception rejected — discrepancy confirmed",
        )
        return exception

    async def ignore(
        self,
        exception_id: str,
        actor: str = "finance_officer",
        notes: Optional[str] = None,
        organization_id: str = "org_default",
    ) -> Optional[FinovaException]:
        """Ignore an exception."""
        exception = await self.get(exception_id, organization_id)
        if not exception:
            return None

        exception.status = ExceptionStatus.IGNORED
        exception.resolved_by = actor
        exception.resolved_at = datetime.utcnow()
        exception.notes = notes
        await self._update(exception)

        await self._audit.log(
            event_type=AuditEventType.EXCEPTION_IGNORED,
            organization_id=organization_id,
            entity_type="exception",
            entity_id=exception_id,
            actor=actor,
            message="Exception ignored",
        )
        return exception

    async def get(self, exception_id: str, organization_id: Optional[str] = None) -> Optional[FinovaException]:
        """Retrieve an exception by ID."""
        query: Dict[str, Any] = {"exception_id": exception_id}
        if organization_id and organization_id != "org_default":
            query["organization_id"] = organization_id

        if self._db is not None:
            doc = await self._db.exceptions.find_one(query)
            if doc:
                doc.pop("_id", None)
                return FinovaException(**doc)
            return None

        if exception_id in memory_exceptions:
            d = memory_exceptions[exception_id].copy()
            d.pop("_id", None)
            return FinovaException(**d)
        return None

    async def list_exceptions(
        self,
        status: Optional[ExceptionStatus] = None,
        processing_run_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> List[FinovaException]:
        """List exceptions with optional filtering."""
        query: Dict[str, Any] = {}
        if status:
            query["status"] = status.value
        if processing_run_id:
            query["processing_run_id"] = processing_run_id
        if organization_id and organization_id != "org_default":
            query["organization_id"] = organization_id

        if self._db is not None:
            cursor = self._db.exceptions.find(query).sort("created_at", -1).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            exceptions = []
            for doc in docs:
                doc.pop("_id", None)
                try:
                    exceptions.append(FinovaException(**doc))
                except Exception as exc:
                    logger.warning("Failed to parse exception doc: %s", exc)
            return exceptions

        all_e = []
        for e in memory_exceptions.values():
            if status and e.get("status") != status.value:
                continue
            if processing_run_id and e.get("processing_run_id") != processing_run_id:
                continue
            if organization_id and organization_id != "org_default" and e.get("organization_id") != organization_id:
                continue
            d = e.copy()
            d.pop("_id", None)
            all_e.append(FinovaException(**d))

        all_e.sort(key=lambda x: x.created_at, reverse=True)
        return all_e[skip:skip+limit]

    async def _persist(self, exception: FinovaException) -> None:
        memory_exceptions[exception.exception_id] = dict_to_mongo(exception)
        if self._db is not None:
            try:
                await self._db.exceptions.insert_one(dict_to_mongo(exception))
            except Exception as exc:
                logger.error("Failed to persist exception: %s", exc)

    async def _update(self, exception: FinovaException) -> None:
        memory_exceptions[exception.exception_id] = dict_to_mongo(exception)
        if self._db is not None:
            try:
                await self._db.exceptions.replace_one(
                    {"exception_id": exception.exception_id},
                    dict_to_mongo(exception),
                    upsert=True,
                )
            except Exception as exc:
                logger.error("Failed to update exception: %s", exc)


def _classify_exception(result: ReconciliationResult):
    """Determine exception type and severity from reconciliation result."""
    status = result.status
    diff = result.difference or Decimal("0")

    if status == ReconciliationStatus.DUPLICATE:
        return (
            ExceptionType.DUPLICATE,
            ExceptionSeverity.HIGH,
            f"Transaction {result.transaction_id} appears to be a duplicate.",
        )

    if status == ReconciliationStatus.MISSING:
        return (
            ExceptionType.MISSING_TRANSACTION,
            ExceptionSeverity.CRITICAL,
            f"Transaction {result.transaction_id} has no matching record.",
        )

    if diff > Decimal("1000"):
        return (
            ExceptionType.AMOUNT_MISMATCH,
            ExceptionSeverity.CRITICAL,
            f"Amount discrepancy of ₹{diff:.2f} exceeds critical threshold.",
        )

    if diff > Decimal("100"):
        return (
            ExceptionType.AMOUNT_MISMATCH,
            ExceptionSeverity.HIGH,
            f"Amount discrepancy of ₹{diff:.2f} requires investigation.",
        )

    if not result.signals or (result.signals and not result.signals.reference_match):
        return (
            ExceptionType.MISSING_REFERENCE,
            ExceptionSeverity.MEDIUM,
            f"Transaction {result.transaction_id} missing reference ID — cannot confirm match.",
        )

    return (
        ExceptionType.AMOUNT_MISMATCH,
        ExceptionSeverity.LOW,
        f"Minor discrepancy of ₹{diff:.2f} — requires review.",
    )
