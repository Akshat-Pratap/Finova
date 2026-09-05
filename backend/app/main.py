"""Finova — FastAPI Application Entry Point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import connect_db, close_db
from app.core.logging_config import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.api import (
    health, auth, organizations, datasets, transactions, reconciliation,
    exceptions, investigations, integrations, analytics, forecasting, reports, razorpay, audit_logs
)

# Configure logging before anything else
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting %s (%s)...", settings.app_name, settings.environment)
    try:
        await connect_db()
    except Exception as exc:
        logger.warning("Database connection failed at startup: %s. Running in graceful memory fallback mode.", exc)
    yield
    await close_db()
    logger.info("%s shutdown complete.", settings.app_name)


app = FastAPI(
    title="Finova — AI-Powered Finance Controller",
    description=(
        "Production-grade financial reconciliation and operations platform. "
        "Integrates deterministic matching, confidence scoring, AI discrepancy investigation, "
        "human-in-the-loop exception workflows, and immutable audit logging."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Request ID correlation & access logging middleware
app.add_middleware(RequestIdMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Production Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Register all routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(datasets.router)
app.include_router(transactions.router)
app.include_router(reconciliation.router)
app.include_router(exceptions.router)
app.include_router(investigations.router)
app.include_router(integrations.router)
app.include_router(analytics.router)
app.include_router(forecasting.router)
app.include_router(reports.router)
app.include_router(razorpay.router)
app.include_router(audit_logs.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global error handler — returns structured errors without exposing internal stack traces."""
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error("[%s] Unhandled exception on %s: %s", req_id, request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred. Please try again.",
                "request_id": req_id,
            },
        },
    )


@app.get("/", include_in_schema=False)
async def root():
    return {
        "app": settings.app_name,
        "version": "1.0.0",
        "mode": "SANDBOX" if settings.is_demo_mode else "PRODUCTION",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
