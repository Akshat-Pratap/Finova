"""Finova — AI Investigator.

Orchestrates AI investigation for ambiguous reconciliation cases.
Selects the appropriate provider (Gemini or Fallback).
Applies guardrails, caching, and audit logging.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings
from app.models.investigation import AIInvestigation
from app.models.reconciliation import ReconciliationResult
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.bank_transaction import BankTransaction
from app.models.settlement import Settlement
from app.services.ai_engine.provider import AIProvider
from app.services.ai_engine.gemini_provider import GeminiProvider
from app.services.ai_engine.fallback import FallbackAIProvider
from app.services.ai_engine.prompts import build_investigation_prompt
from app.services.ai_engine.schemas import AIInvestigationResponse
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)

# Simple in-memory cache: investigation_key → AIInvestigation
_investigation_cache: Dict[str, AIInvestigation] = {}


def _get_provider() -> AIProvider:
    """Return the appropriate AI provider based on configuration."""
    if settings.is_demo_mode:
        return FallbackAIProvider()
    try:
        provider = GeminiProvider()
        if provider.is_available:
            return provider
    except Exception as exc:
        logger.warning("Gemini provider unavailable: %s — using fallback", exc)
    return FallbackAIProvider()


def _cache_key(txn_id: str, run_id: str) -> str:
    return f"{run_id}:{txn_id}"


async def investigate_transaction(
    txn: Transaction,
    reconciliation_result: ReconciliationResult,
    exception_id: str,
    processing_run_id: str,
    invoice: Optional[Invoice] = None,
    bank_txn: Optional[BankTransaction] = None,
    settlement: Optional[Settlement] = None,
    organization_id: str = "org_default",
) -> AIInvestigation:
    """
    Run an AI investigation on an ambiguous transaction.

    Checks cache first to avoid redundant API calls.
    Falls back to deterministic investigator on AI failure.
    Tracks latency, hashes prompt context, and versions the prompt.
    """
    cache_key = _cache_key(txn.transaction_id, processing_run_id)
    if cache_key in _investigation_cache:
        logger.debug("Cache hit for investigation: %s", cache_key)
        return _investigation_cache[cache_key]

    provider = _get_provider()
    is_fallback = isinstance(provider, FallbackAIProvider)
    retry_count = 0

    # Build context and compute hash
    context = _build_context(
        txn=txn,
        result=reconciliation_result,
        invoice=invoice,
        bank_txn=bank_txn,
        settlement=settlement,
    )
    import hashlib
    import json
    context_str = json.dumps(context, sort_keys=True, default=str)
    context_hash = hashlib.sha256(context_str.encode("utf-8")).hexdigest()[:16]

    prompt = build_investigation_prompt(context)
    response_data: Optional[Dict[str, Any]] = None

    start_time = time.perf_counter()
    try:
        response_data = await provider.investigate(context=context, prompt=prompt)
    except Exception as exc:
        logger.error("AI investigation failed: %s — using fallback", exc)
        if not is_fallback:
            fallback = FallbackAIProvider()
            response_data = await fallback.investigate(context=context, prompt=prompt)
            is_fallback = True
            retry_count = 1

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    if not response_data:
        # Hard fallback — insufficient evidence
        response_data = {
            "finding": "Investigation failed — manual review required",
            "reason": "AI investigation encountered an error. Manual review required.",
            "confidence": 0.0,
            "recommendation": "MANUAL_REVIEW",
            "requires_manual_review": True,
            "evidence": ["AI investigation failed"],
        }
        is_fallback = True

    investigation = AIInvestigation(
        investigation_id=f"INV-{uuid.uuid4().hex[:8].upper()}",
        exception_id=exception_id,
        organization_id=organization_id,
        transaction_id=txn.transaction_id,
        processing_run_id=processing_run_id,
        provider=provider.provider_name,
        prompt_version=settings.prompt_version,
        request_context_hash=context_hash,
        latency_ms=latency_ms,
        input_context=context,
        finding=response_data.get("finding", ""),
        reason=response_data.get("reason", ""),
        confidence=float(response_data.get("confidence", 0.0)),
        recommendation=response_data.get("recommendation", "MANUAL_REVIEW"),
        requires_manual_review=response_data.get("requires_manual_review", True),
        evidence=response_data.get("evidence", []),
        is_fallback=is_fallback,
        retry_count=retry_count,
    )

    _investigation_cache[cache_key] = investigation
    logger.info(
        "Investigation complete: %s | finding=%s confidence=%.2f (latency: %.1fms)",
        investigation.investigation_id, investigation.finding, investigation.confidence, latency_ms,
    )
    return investigation


def _build_context(
    txn: Transaction,
    result: ReconciliationResult,
    invoice: Optional[Invoice],
    bank_txn: Optional[BankTransaction],
    settlement: Optional[Settlement],
) -> Dict[str, Any]:
    """Build structured context dict for AI investigation."""
    from app.utils.helpers import dict_to_mongo

    return {
        "transaction": dict_to_mongo(txn),
        "invoice": dict_to_mongo(invoice) if invoice else {},
        "bank_transaction": dict_to_mongo(bank_txn) if bank_txn else {},
        "settlement": dict_to_mongo(settlement) if settlement else {},
        "confidence_signals": dict_to_mongo(result.signals),
        "confidence_score": result.confidence,
        "rule_results": result.signals.model_dump() if result.signals else {},
    }
