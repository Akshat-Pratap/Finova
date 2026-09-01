"""Finova — Request ID Middleware & Correlation."""
from __future__ import annotations

import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("finova.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Attaches a unique Request-ID to each incoming request and response headers.
    Logs structured access metrics with latency.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        # Log access info (avoid logging sensitive endpoints in detail)
        if request.url.path not in ("/api/v1/health", "/"):
            logger.info(
                "[%s] %s %s %d (%.2fms)",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        return response
