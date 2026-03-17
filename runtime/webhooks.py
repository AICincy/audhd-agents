"""Notion webhook endpoint router.

Receives, verifies, deduplicates, and routes Notion webhook events
to the cognitive pipeline via pipeline_bridge.

Endpoints:
    POST /webhooks/notion     - Receive webhook events
    GET  /webhooks/notion     - Health check for webhook subsystem
    POST /webhooks/test       - Dev-only echo endpoint (staging only)
"""

from __future__ import annotations

import json
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from runtime.auth import verify_webhook
from runtime.pipeline_bridge import dispatch_event, is_ready as bridge_ready
from runtime.webhook_schemas import (
    EventCategory,
    ProcessedEvent,
    VerificationChallenge,
    WebhookEvent,
    WebhookEventType,
    WebhookResponse,
)

logger = logging.getLogger("audhd_agents.webhooks")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ---------------------------------------------------------------------------
# Idempotency: LRU dedup cache (event_id -> timestamp)
# ---------------------------------------------------------------------------

class EventDeduplicator:
    """LRU cache for webhook event dedup. Thread-safe for single-worker uvicorn."""

    def __init__(self, max_size: int = 10_000, ttl_seconds: int = 3600):
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def is_duplicate(self, event_id: str) -> bool:
        """Check if event was already processed. Adds to cache if new."""
        now = time.time()

        # Evict expired entries
        expired = [
            eid for eid, ts in self._cache.items()
            if now - ts > self._ttl
        ]
        for eid in expired:
            del self._cache[eid]

        if event_id in self._cache:
            self._cache.move_to_end(event_id)
            return True

        # Evict oldest if at capacity
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[event_id] = now
        return False

    @property
    def size(self) -> int:
        return len(self._cache)


# Module-level dedup instance
_dedup = EventDeduplicator()


# ---------------------------------------------------------------------------
# Event Handlers (category-based routing)
# ---------------------------------------------------------------------------

class EventRouter:
    """Route webhook events to appropriate handlers by category."""

    def __init__(self) -> None:
        self._handlers: dict[EventCategory, list[Any]] = {
            cat: [] for cat in EventCategory
        }
        self._global_handlers: list[Any] = []

    def register(self, category: EventCategory, handler: Any) -> None:
        self._handlers[category].append(handler)

    def register_global(self, handler: Any) -> None:
        """Handlers that run for every event (logging, metrics, etc.)."""
        self._global_handlers.append(handler)

    async def dispatch(self, event: WebhookEvent) -> list[str]:
        """Dispatch event to registered handlers. Returns handler names that ran."""
        executed = []

        # Global handlers first
        for handler in self._global_handlers:
            try:
                await handler(event)
                executed.append(handler.__name__)
            except Exception as exc:
                logger.error(
                    "Global handler %s failed: %s",
                    handler.__name__,
                    exc,
                    exc_info=True,
                )

        # Category-specific handlers
        for handler in self._handlers.get(event.category, []):
            try:
                await handler(event)
                executed.append(handler.__name__)
            except Exception as exc:
                logger.error(
                    "Handler %s failed for %s: %s",
                    handler.__name__,
                    event.type.value,
                    exc,
                    exc_info=True,
                )

        return executed


# Module-level event router
_event_router = EventRouter()


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------

async def log_event(event: WebhookEvent) -> None:
    """Structured log for every webhook event."""
    logger.info(
        json.dumps({
            "event": "webhook_received",
            "event_id": event.id,
            "event_type": event.type.value,
            "workspace_id": event.workspace_id,
            "entity_id": event.data.entity.id,
            "entity_type": event.data.entity.type,
            "author": event.data.author.id if event.data.author else None,
            "timestamp": event.timestamp,
        })
    )


async def handle_page_event(event: WebhookEvent) -> None:
    """Process page lifecycle events through the cognitive pipeline."""
    entity = event.data.entity

    logger.info(
        json.dumps({
            "event": "page_event_routing",
            "action": event.action,
            "page_id": entity.id,
            "page_title": entity.title,
            "updated_properties": event.data.updated_properties,
        })
    )

    result = await dispatch_event(event)
    if result:
        logger.info(
            json.dumps({
                "event": "page_event_skill_result",
                "action": event.action,
                "page_id": entity.id,
                "skill_id": result.get("skill_id"),
                "has_error": "error" in result,
            })
        )


async def handle_database_event(event: WebhookEvent) -> None:
    """Process database lifecycle events through the cognitive pipeline."""
    logger.info(
        json.dumps({
            "event": "database_event_routing",
            "action": event.action,
            "database_id": event.data.entity.id,
        })
    )

    await dispatch_event(event)


async def handle_data_source_event(event: WebhookEvent) -> None:
    """Process data source events through the cognitive pipeline."""
    logger.info(
        json.dumps({
            "event": "data_source_event_routing",
            "action": event.action,
            "data_source_id": event.data.entity.id,
            "updated_properties": event.data.updated_properties,
        })
    )

    await dispatch_event(event)


async def handle_view_event(event: WebhookEvent) -> None:
    """Process view lifecycle events (log only, no skill trigger)."""
    logger.info(
        json.dumps({
            "event": "view_event_processed",
            "action": event.action,
            "view_id": event.data.entity.id,
        })
    )


# Register handlers
_event_router.register_global(log_event)
_event_router.register(EventCategory.PAGE, handle_page_event)
_event_router.register(EventCategory.DATABASE, handle_database_event)
_event_router.register(EventCategory.DATA_SOURCE, handle_data_source_event)
_event_router.register(EventCategory.VIEW, handle_view_event)


# ---------------------------------------------------------------------------
# Webhook Endpoints
# ---------------------------------------------------------------------------

@router.post("/notion", response_model=WebhookResponse)
async def receive_webhook(request: Request, body: bytes = Depends(verify_webhook)):
    """Receive and process Notion webhook events.

    Flow:
    1. HMAC signature verified (via verify_webhook dependency)
    2. Parse body as VerificationChallenge or WebhookEvent
    3. Dedup check by event_id
    4. Route to category handlers -> cognitive pipeline
    5. Return 200 immediately (async processing for heavy work)
    """
    started_at = time.time()

    try:
        raw = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    # Handle verification challenge (subscription setup)
    if raw.get("type") == "url_verification":
        challenge = VerificationChallenge(**raw)
        return {"challenge": challenge.challenge}

    # Parse as webhook event
    try:
        event = WebhookEvent(**raw)
    except Exception as exc:
        logger.error("Failed to parse webhook event: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid webhook event: {exc}",
        )

    # Idempotency check
    if _dedup.is_duplicate(event.id):
        logger.info(
            json.dumps({
                "event": "webhook_deduplicated",
                "event_id": event.id,
                "event_type": event.type.value,
            })
        )
        return WebhookResponse(
            status="ok",
            event_id=event.id,
            processed=False,
            message="Duplicate event, already processed",
        )

    # Dispatch to handlers (which now call pipeline_bridge)
    handlers_run = await _event_router.dispatch(event)

    processing_ms = (time.time() - started_at) * 1000

    logger.info(
        json.dumps({
            "event": "webhook_processed",
            "event_id": event.id,
            "event_type": event.type.value,
            "handlers_executed": handlers_run,
            "processing_ms": round(processing_ms, 2),
            "dedup_cache_size": _dedup.size,
        })
    )

    return WebhookResponse(
        status="ok",
        event_id=event.id,
        processed=True,
        message=f"Processed by {len(handlers_run)} handler(s)",
    )


@router.get("/notion")
async def webhook_health():
    """Health check for webhook subsystem."""
    return {
        "status": "ok",
        "pipeline_bridge": "ready" if bridge_ready() else "not_initialized",
        "dedup_cache_size": _dedup.size,
        "registered_categories": [cat.value for cat in EventCategory],
        "event_types_supported": len(WebhookEventType),
    }


@router.post("/test")
async def webhook_test(request: Request):
    """Dev-only echo endpoint. Returns parsed body without processing.

    Only available outside production. Returns 404 in production.
    """
    import os
    if os.getenv("APP_ENV", "development") == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    app_env = getattr(request.app.state, "runtime", None)
    if app_env and hasattr(app_env, "settings"):
        if app_env.settings.app_env == "production":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found",
            )

    body = await request.body()
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        parsed = {"raw": body.decode("utf-8", errors="replace")}

    # AUDIT-FIX: P1-10-early -- strip sensitive headers from echo response
    _SENSITIVE_HEADER_NAMES = frozenset({
        "authorization", "cookie", "x-api-key",
    })
    _SENSITIVE_HEADER_SUBSTRINGS = ("secret", "token")

    safe_headers: dict[str, str] = {}
    for key, value in request.headers.items():
        lower_key = key.lower()
        if lower_key in _SENSITIVE_HEADER_NAMES:
            continue
        if any(s in lower_key for s in _SENSITIVE_HEADER_SUBSTRINGS):
            continue
        safe_headers[key] = value

    return {
        "echo": parsed,
        "headers": safe_headers,
        "method": request.method,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Public API for external handler registration
# ---------------------------------------------------------------------------

def register_handler(category: EventCategory, handler: Any) -> None:
    """Register a custom event handler for a category."""
    _event_router.register(category, handler)


def register_global_handler(handler: Any) -> None:
    """Register a handler that runs for all events."""
    _event_router.register_global(handler)


def get_deduplicator() -> EventDeduplicator:
    """Access the dedup cache (for testing/metrics)."""
    return _dedup
