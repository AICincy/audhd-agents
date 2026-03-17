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
        # AUDIT-FIX: P2-10 -- validate X-Request-ID as UUID format
        raw_id = request.headers.get("X-Request-ID", "")
        try:
            request_id = str(uuid.UUID(raw_id))
        except (ValueError, AttributeError):
            request_id = str(uuid.uuid4())
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
    if cors_origins is not None:
        origins: list[str] = cors_origins
    else:
        # Default to an empty allowlist; rely on CORS_ALLOWED_ORIGINS or
        # explicit cors_origins to configure allowed origins.
        origins = []

    # AUDIT-FIX: P1-5 -- replace ngrok regex with env-based allowlist
    import os
    cors_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    if cors_env:
        extra_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
        if origins:
            origins = origins + extra_origins
        else:
            origins = extra_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Notion-Signature",
            "X-Notion-Timestamp",
        ],
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
