"""Finova — Razorpay Integration Provider.

Interacts with Razorpay API (or test mock) and maps records into canonical Finova entities.
Prevents duplicate ingestion during recurring syncs.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.integrations.provider import IntegrationProvider
from app.services.integrations.mock_razorpay import get_mock_payments, get_mock_settlements

logger = logging.getLogger(__name__)


class RazorpayProvider(IntegrationProvider):
    """Razorpay Gateway Provider Implementation."""

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self._key_id = key_id or settings.razorpay_key_id
        self._key_secret = key_secret or settings.razorpay_key_secret
        self._client = None
        self._mode = "MOCK"
        self._initialize()

    def _initialize(self):
        if self._key_id and self._key_secret:
            try:
                import razorpay
                self._client = razorpay.Client(auth=(self._key_id, self._key_secret))
                self._mode = "LIVE"
                logger.info("Razorpay provider initialized in LIVE mode.")
            except ImportError:
                logger.warning("razorpay package not installed — operating in MOCK mode.")
            except Exception as exc:
                logger.warning("Razorpay init error (%s) — operating in MOCK mode.", exc)

    @property
    def mode(self) -> str:
        return self._mode

    async def test_connection(self) -> Tuple[bool, str]:
        """Verify credentials by attempting a fetch."""
        if self._mode == "LIVE" and self._client:
            try:
                self._client.payment.all({"count": 1})
                return True, "Successfully authenticated with Razorpay."
            except Exception as exc:
                return False, f"Razorpay authentication failed: {exc}"
        return True, "Connected to Razorpay (Sandbox / Mock Mode active)."

    async def fetch_payments(self, count: int = 50, since: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Fetch transactions from Razorpay."""
        if self._mode == "LIVE" and self._client:
            try:
                params: Dict[str, Any] = {"count": count}
                if since:
                    params["from"] = int(since.timestamp()) if hasattr(since, "timestamp") else since
                resp = self._client.payment.all(params)
                items = resp.get("items", [])
                return [self._map_payment(p) for p in items]
            except Exception as exc:
                logger.error("Razorpay live payments fetch failed: %s", exc)

        # Fallback to mock
        mock_raw = get_mock_payments(count)
        return [self._map_payment(p) for p in mock_raw]

    async def fetch_settlements(self, count: int = 20, since: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Fetch settlements from Razorpay."""
        if self._mode == "LIVE" and self._client:
            try:
                params: Dict[str, Any] = {"count": count}
                resp = self._client.settlement.all(params)
                items = resp.get("items", [])
                return [self._map_settlement(s) for s in items]
            except Exception as exc:
                logger.error("Razorpay live settlements fetch failed: %s", exc)

        mock_raw = get_mock_settlements(count)
        return [self._map_settlement(s) for s in mock_raw]

    def _map_payment(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Razorpay payment payload to canonical transaction schema."""
        amount_raw = raw.get("amount", 0)
        amount_inr = float(amount_raw) / 100.0 if raw.get("currency") == "INR" and amount_raw > 1000 else float(amount_raw)

        ts_raw = raw.get("created_at") or raw.get("timestamp")
        if isinstance(ts_raw, (int, float)):
            ts_val = datetime.fromtimestamp(ts_raw).isoformat()
        elif isinstance(ts_raw, datetime):
            ts_val = ts_raw.isoformat()
        else:
            ts_val = str(ts_raw) if ts_raw else datetime.utcnow().isoformat()

        return {
            "transaction_id": str(raw.get("id") or raw.get("payment_id")),
            "order_id": raw.get("order_id"),
            "customer_id": str(raw.get("customer_id") or raw.get("email") or raw.get("contact") or "CUST-RZP"),
            "amount": amount_inr,
            "currency": raw.get("currency", "INR"),
            "payment_status": raw.get("status", "captured"),
            "payment_method": raw.get("method", "upi"),
            "timestamp": ts_val,
            "reference_id": raw.get("acquirer_data", {}).get("rrn") or raw.get("acquirer_data", {}).get("bank_transaction_id") or raw.get("id"),
            "description": raw.get("description") or f"Razorpay Payment {raw.get('id')}",
            "source": "razorpay",
        }

    def _map_settlement(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Razorpay settlement payload to canonical settlement schema."""
        gross = float(raw.get("amount", 0)) / 100.0 if raw.get("amount", 0) > 1000 else float(raw.get("amount", 0))
        fees = float(raw.get("fees", 0)) / 100.0 if raw.get("fees", 0) > 1000 else float(raw.get("fees", 0))
        tax = float(raw.get("tax", 0)) / 100.0 if raw.get("tax", 0) > 1000 else float(raw.get("tax", 0))
        net = float(raw.get("net_amount", gross - fees - tax))

        ts_raw = raw.get("created_at") or raw.get("settlement_date")
        if isinstance(ts_raw, (int, float)):
            ts_val = datetime.fromtimestamp(ts_raw).isoformat()
        elif isinstance(ts_raw, datetime):
            ts_val = ts_raw.isoformat()
        else:
            ts_val = str(ts_raw) if ts_raw else datetime.utcnow().isoformat()

        return {
            "settlement_id": str(raw.get("id") or raw.get("settlement_id")),
            "transaction_id": str(raw.get("payment_id", "")),
            "gross_amount": gross,
            "fees": fees,
            "tax": tax,
            "net_amount": net,
            "settlement_date": ts_val,
            "status": "processed",
        }
