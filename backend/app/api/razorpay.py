"""Finova — Razorpay Integration API."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/razorpay", tags=["Razorpay"])


@router.get("/payments", summary="Get Razorpay payments (mock or live)")
async def get_payments(count: int = 10):
    """Fetch recent Razorpay payments."""
    from app.services.integrations.razorpay_service import RazorpayService
    svc = RazorpayService()
    payments = svc.get_payments(count)
    return {"success": True, "mode": svc.mode, "payments": payments}


@router.get("/settlements", summary="Get Razorpay settlements")
async def get_settlements(count: int = 5):
    """Fetch recent Razorpay settlements."""
    from app.services.integrations.razorpay_service import RazorpayService
    svc = RazorpayService()
    settlements = svc.get_settlements(count)
    return {"success": True, "mode": svc.mode, "settlements": settlements}
