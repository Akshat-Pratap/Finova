"""Finova — Cash Position Forecasting API Routes."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.core.database import get_db, is_connected
from app.core.config import settings
from app.core.auth_middleware import AuthenticatedContext, get_auth_context
from app.models.transaction import Transaction
from app.models.settlement import Settlement
from app.services.forecasting.cash_forecaster import generate_forecast, generate_demo_forecast
from app.services.memory_store import memory_results
from app.utils.helpers import dict_to_mongo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Forecasting"])


@router.get("/forecast", summary="Get cash position forecast")
async def get_cash_forecast(
    sandbox: bool = Query(False, description="Force sandbox/demo forecast"),
    ctx: Optional[AuthenticatedContext] = Depends(get_auth_context),
):
    """Generate and return a 14-day cash forecast with transparent methodology."""
    try:
        db = get_db() if is_connected() else None
    except Exception:
        db = None

    org_id = ctx.org_id if ctx else "org_default"

    # Explicit sandbox mode
    if sandbox or settings.is_demo_mode:
        demo = generate_demo_forecast()
        data = dict_to_mongo(demo)
        data["mode"] = "SANDBOX"
        data["methodology"] = "Simulated 14-day moving average cash model (Demo Data)."
        return {"success": True, "forecast": data}

    # Real data fetch
    txns = []
    settlements = []

    if db is not None:
        cursor = db.reconciliation_results.find({"organization_id": org_id}).sort("created_at", -1).limit(500)
        docs = await cursor.to_list(length=500)
        for d in docs:
            d.pop("_id", None)
            try:
                amt = Decimal(str(d.get("actual_amount") or d.get("expected_amount") or 0))
                txns.append(Transaction(
                    transaction_id=d.get("transaction_id", ""),
                    customer_id=d.get("customer_id", "UNKNOWN"),
                    amount=amt,
                    timestamp=d.get("created_at") or datetime.utcnow(),
                    organization_id=org_id,
                ))
            except Exception:
                pass
    else:
        # Memory check
        for r_list in memory_results.values():
            for d in r_list:
                if not org_id or org_id == "org_default" or d.get("organization_id") == org_id:
                    try:
                        amt = Decimal(str(d.get("actual_amount") or d.get("expected_amount") or 0))
                        txns.append(Transaction(
                            transaction_id=d.get("transaction_id", ""),
                            customer_id=d.get("customer_id", "UNKNOWN"),
                            amount=amt,
                            timestamp=d.get("created_at") or datetime.utcnow(),
                            organization_id=org_id,
                        ))
                    except Exception:
                        pass

    if len(txns) < 5:
        return {
            "success": True,
            "forecast": {
                "status": "INSUFFICIENT_DATA",
                "mode": "PRODUCTION",
                "observations_count": len(txns),
                "minimum_required": 5,
                "message": (
                    "Insufficient historical transactions to compute a reliable cash forecast. "
                    "Upload a dataset or connect Razorpay to populate your organization's forecast."
                ),
                "current_cash": 0.0,
                "risk_level": "LOW",
                "daily_breakdown": [],
            },
        }

    forecast = generate_forecast(txns, settlements)
    res_dict = dict_to_mongo(forecast)
    res_dict["mode"] = "PRODUCTION"
    res_dict["observations_count"] = len(txns)
    res_dict["methodology"] = "Weighted historical cash flow velocity & settlement forecast."
    return {"success": True, "forecast": res_dict}
