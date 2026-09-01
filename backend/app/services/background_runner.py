"""Finova — Background Job Runner.

Executes long-running reconciliation jobs asynchronously without blocking HTTP requests,
tracking live progress, elapsed time, and status.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BackgroundJob:
    """State of an asynchronous background reconciliation task."""

    def __init__(
        self,
        job_id: str,
        organization_id: str,
        run_id: str,
        description: str = "",
    ):
        self.job_id = job_id
        self.organization_id = organization_id
        self.run_id = run_id
        self.description = description
        self.status = JobStatus.QUEUED
        self.progress_percent = 0.0
        self.records_total = 0
        self.records_processed = 0
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "organization_id": self.organization_id,
            "run_id": self.run_id,
            "description": self.description,
            "status": self.status.value,
            "progress_percent": round(self.progress_percent, 1),
            "records_total": self.records_total,
            "records_processed": self.records_processed,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
        }


# Global in-memory job registry
_jobs: Dict[str, BackgroundJob] = {}


class BackgroundJobRunner:
    """Dispatches and tracks asynchronous operations."""

    @staticmethod
    def create_job(organization_id: str, run_id: str, description: str = "") -> BackgroundJob:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = BackgroundJob(
            job_id=job_id,
            organization_id=organization_id,
            run_id=run_id,
            description=description,
        )
        _jobs[job_id] = job
        return job

    @staticmethod
    def get_job(job_id: str) -> Optional[BackgroundJob]:
        return _jobs.get(job_id)

    @staticmethod
    def spawn_task(job_id: str, coroutine_func: Callable[[], Coroutine[Any, Any, Any]]) -> asyncio.Task:
        """Spawn a detached task with automatic error capture and status updating."""
        job = _jobs.get(job_id)

        async def _wrapper():
            if job:
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.utcnow()
            try:
                result = await coroutine_func()
                if job:
                    job.status = JobStatus.COMPLETED
                    job.progress_percent = 100.0
                    job.completed_at = datetime.utcnow()
                    if isinstance(result, dict):
                        job.result = result
            except Exception as exc:
                logger.error("Background job %s failed: %s", job_id, exc, exc_info=True)
                if job:
                    job.status = JobStatus.FAILED
                    job.error = str(exc)
                    job.completed_at = datetime.utcnow()

        task = asyncio.create_task(_wrapper())
        return task
