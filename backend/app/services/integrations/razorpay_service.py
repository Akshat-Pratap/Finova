"""Finova — Razorpay Service.

Abstracts Razorpay API integration with automatic fallback to mock mode.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class RazorpayService:
    """
    Razorpay integration service.

    Supports:
    - Live/Test mode (when credentials provided)
    - Mock/Demo mode (default)
    """

    def __init__(self):
        self._client = None
        self._mode = "MOCK"
        self._initialize()

    def _initialize(self):
        if settings.razorpay_key_id and settings.razorpay_key_secret:
            try:
                # Import only if credentials present
                import razorpay  # type: ignore
                self._client = razorpay.Client(
                    auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
                )
                self._mode = "LIVE"
                logger.info("Razorpay client initialized in LIVE mode.")
            except ImportError:
                logger.warning("razorpay package not installed — using MOCK mode.")
            except Exception as exc:
                logger.warning("Razorpay init failed (%s) — using MOCK mode.", exc)

    @property
    def mode(self) -> str:
        return self._mode

    def get_payments(self, count: int = 10) -> List[Dict]:
        """Fetch recent payments."""
        if self._mode == "LIVE" and self._client:
            try:
                resp = self._client.payment.all({"count": count})
                return resp.get("items", [])
            except Exception as exc:
                logger.error("Razorpay payment fetch failed: %s", exc)
        from app.services.integrations.mock_razorpay import get_mock_payments
        return get_mock_payments(count)

    def get_settlements(self, count: int = 5) -> List[Dict]:
        """Fetch recent settlements."""
        if self._mode == "LIVE" and self._client:
            try:
                resp = self._client.settlement.all({"count": count})
                return resp.get("items", [])
            except Exception as exc:
                logger.error("Razorpay settlement fetch failed: %s", exc)
        from app.services.integrations.mock_razorpay import get_mock_settlements
        return get_mock_settlements(count)
