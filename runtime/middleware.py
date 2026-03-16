"""ASGI middleware for the AuDHD runtime.

- Request ID injection (X-Request-ID)
- Structured request/response logging
- CORS configuration
- Timing headers
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("audhd_agents.middleware")


# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID into every request/response for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Structured Logging Middleware
# ---------------------------------------------------------------------------

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with structured JSON. Skip health checks."""

    SKIP_PATHS = {"/healthz", "/readyz", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        started_at = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - started_at) * 1000
        request_id = getattr(request.state, "request_id", "unknown")

        logger.info(
            json.dumps({
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id,
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent", "")[:100],
            })
        )

        response.headers["X-Response-Time-Ms"] = str(round(duration_ms, 2))
        return response


# ---------------------------------------------------------------------------
# Timing Header Middleware
# ---------------------------------------------------------------------------

class ServerTimingMiddleware(BaseHTTPMiddleware):
    """Add Server-Timing header for performance observability."""

    async def dispatch(self, request: Request, call_next):
        started_at = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - started_at) * 1000
        response.headers["Server-Timing"] = f"total;dur={duration_ms:.1f}"
        return response


# ---------------------------------------------------------------------------
# Middleware Registration
# ---------------------------------------------------------------------------

def register_middleware(app: FastAPI, *, cors_origins: list[str] | None = None) -> None:
    """Register all middleware on the FastAPI app.

    Order matters (outermost runs first):
    1. CORS (must be outermost for preflight)
    2. Request ID
    3. Structured logging
    4. Server timing
    """
    # CORS
    origins = cors_origins or [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://.*\.ngrok-free\.app",
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Response-Time-Ms",
            "Server-Timing",
        ],
    )

    # Order: last added = outermost
    app.add_middleware(ServerTimingMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
