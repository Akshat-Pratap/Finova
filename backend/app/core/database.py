"""Finova — MongoDB Database Connection."""
from __future__ import annotations

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    """Initialize MongoDB connection."""
    global _client, _db
    try:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
        )
        # Verify connection
        await _client.admin.command("ping")
        _db = _client[settings.mongodb_database]
        logger.info("MongoDB connected: %s / %s", settings.mongodb_uri, settings.mongodb_database)
        await _ensure_indexes()
    except Exception as exc:
        logger.error("MongoDB connection failed: %s", exc)
        _client = None
        _db = None
        raise


async def close_db() -> None:
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database instance."""
    if _db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _db


def is_connected() -> bool:
    """Check if database is connected."""
    return _db is not None


async def _ensure_indexes() -> None:
    """Create necessary indexes for all collections with tenant isolation."""
    db = get_db()

    # Users
    await db.users.create_index([("user_id", ASCENDING)], unique=True)
    await db.users.create_index([("email", ASCENDING)], unique=True)
    await db.users.create_index([("created_at", DESCENDING)])

    # Organizations
    await db.organizations.create_index([("organization_id", ASCENDING)], unique=True)
    await db.organizations.create_index([("slug", ASCENDING)], unique=True)

    # Memberships
    await db.memberships.create_index([("membership_id", ASCENDING)], unique=True)
    await db.memberships.create_index([("organization_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
    await db.memberships.create_index([("user_id", ASCENDING)])

    # Datasets
    await db.datasets.create_index([("dataset_id", ASCENDING)], unique=True)
    await db.datasets.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)])

    # Transactions
    await db.transactions.create_index([("transaction_id", ASCENDING)], unique=True)
    await db.transactions.create_index([("organization_id", ASCENDING), ("transaction_id", ASCENDING)])
    await db.transactions.create_index([("organization_id", ASCENDING), ("customer_id", ASCENDING)])
    await db.transactions.create_index([("organization_id", ASCENDING), ("reference_id", ASCENDING)])
    await db.transactions.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)])
    await db.transactions.create_index([("organization_id", ASCENDING), ("processing_run_id", ASCENDING)])

    # Invoices
    await db.invoices.create_index([("invoice_id", ASCENDING)], unique=True)
    await db.invoices.create_index([("organization_id", ASCENDING), ("customer_id", ASCENDING)])

    # Bank Transactions
    await db.bank_transactions.create_index([("bank_transaction_id", ASCENDING)], unique=True)
    await db.bank_transactions.create_index([("organization_id", ASCENDING), ("reference", ASCENDING)])

    # Settlements
    await db.settlements.create_index([("settlement_id", ASCENDING)], unique=True)
    await db.settlements.create_index([("organization_id", ASCENDING), ("transaction_id", ASCENDING)])

    # Reconciliation Results
    await db.reconciliation_results.create_index([("result_id", ASCENDING)], unique=True)
    await db.reconciliation_results.create_index([("organization_id", ASCENDING), ("transaction_id", ASCENDING)])
    await db.reconciliation_results.create_index([("organization_id", ASCENDING), ("processing_run_id", ASCENDING)])
    await db.reconciliation_results.create_index([("organization_id", ASCENDING), ("status", ASCENDING)])
    await db.reconciliation_results.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)])

    # Exceptions
    await db.exceptions.create_index([("exception_id", ASCENDING)], unique=True)
    await db.exceptions.create_index([("organization_id", ASCENDING), ("exception_id", ASCENDING)])
    await db.exceptions.create_index([("organization_id", ASCENDING), ("transaction_id", ASCENDING)])
    await db.exceptions.create_index([("organization_id", ASCENDING), ("status", ASCENDING)])
    await db.exceptions.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)])

    # Exception Notes / Comments
    await db.exception_notes.create_index([("note_id", ASCENDING)], unique=True)
    await db.exception_notes.create_index([("organization_id", ASCENDING), ("exception_id", ASCENDING)])
    await db.exception_notes.create_index([("created_at", ASCENDING)])

    # AI Investigations
    await db.ai_investigations.create_index([("investigation_id", ASCENDING)], unique=True)
    await db.ai_investigations.create_index([("organization_id", ASCENDING), ("exception_id", ASCENDING)])
    await db.ai_investigations.create_index([("organization_id", ASCENDING), ("transaction_id", ASCENDING)])

    # Audit Logs (hash-chained append-only)
    await db.audit_logs.create_index([("log_id", ASCENDING)], unique=True)
    await db.audit_logs.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)])
    await db.audit_logs.create_index([("organization_id", ASCENDING), ("event_type", ASCENDING)])
    await db.audit_logs.create_index([("organization_id", ASCENDING), ("processing_run_id", ASCENDING)])

    # Processing Runs
    await db.processing_runs.create_index([("run_id", ASCENDING)], unique=True)
    await db.processing_runs.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)])

    # Integrations
    await db.integrations.create_index([("integration_id", ASCENDING)], unique=True)
    await db.integrations.create_index([("organization_id", ASCENDING), ("provider", ASCENDING)], unique=True)

    # Reports
    await db.reports.create_index([("report_id", ASCENDING)], unique=True)
    await db.reports.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)])

    logger.info("Database multi-tenant indexes ensured.")

