"""Finova — Deep Health Check Endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from app.core.config import settings
from app.core.database import is_connected
from app.services.integrations.razorpay_service import RazorpayService

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get(
    "/health",
    summary="Deep Health check",
    description="Returns the live health status of application services, database, AI provider, and integrations.",
)
async def health_check():
    """Deep health check endpoint."""
    db_connected = is_connected()
    rzp = RazorpayService()

    services_status = {
        "application": "healthy",
        "database": "connected" if db_connected else "disconnected (running in graceful memory mode)",
        "ai_provider": settings.ai_provider_name,
        "integrations": f"Razorpay ({rzp.mode} mode)",
    }

    return {
        "status": "healthy" if db_connected else "degraded",
        "environment": settings.environment,
        "app_name": settings.app_name,
        "version": "1.0.0",
        "services": services_status,
        "mode": "SANDBOX" if settings.is_demo_mode else "PRODUCTION",
    }
