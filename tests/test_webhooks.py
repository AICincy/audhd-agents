"""Tests for webhook endpoints and event processing.

Covers:
- Verification challenge response
- Event parsing and routing
- Idempotency / deduplication
- Invalid payload rejection
- HMAC signature verification
- Category-based event dispatch
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from runtime.webhook_schemas import (
    EventCategory,
    ProcessedEvent,
    VerificationChallenge,
    WebhookEvent,
    WebhookEventType,
    WebhookResponse,
)
from runtime.auth import verify_webhook_signature
from runtime.webhooks import EventDeduplicator, EventRouter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test_secret_key_for_hmac_verification_32bytes"


def make_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Generate HMAC-SHA256 signature for test payloads."""
    return "v1=" + hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


def make_event_payload(
    event_type: str = "page.created",
    event_id: str = "evt-test-001",
    entity_id: str = "page-123",
    entity_type: str = "page",
) -> dict:
    """Build a valid webhook event payload."""
    return {
        "id": event_id,
        "type": event_type,
        "timestamp": "2026-03-16T15:00:00.000Z",
        "workspace_id": "ws-test-001",
        "subscription_id": "sub-test-001",
        "api_version": "2026-03-11",
        "data": {
            "entity": {
                "id": entity_id,
                "type": entity_type,
                "title": "Test Page",
            },
            "author": {
                "id": "user-001",
                "type": "user",
                "name": "Test User",
            },
        },
    }


# ---------------------------------------------------------------------------
# WebhookEvent Model Tests
# ---------------------------------------------------------------------------


class TestWebhookEventModel:
    """Test Pydantic model parsing and validation."""

    def test_parse_page_created(self):
        payload = make_event_payload("page.created")
        event = WebhookEvent(**payload)
        assert event.type == WebhookEventType.PAGE_CREATED
        assert event.category == EventCategory.PAGE
        assert event.action == "created"
        assert event.data.entity.id == "page-123"

    def test_parse_database_updated(self):
        payload = make_event_payload("database.updated", entity_type="database")
        event = WebhookEvent(**payload)
        assert event.type == WebhookEventType.DATABASE_UPDATED
        assert event.category == EventCategory.DATABASE

    def test_parse_all_event_types(self):
        """Every WebhookEventType must parse without error."""
        for evt_type in WebhookEventType:
            category = evt_type.value.split(".")[0]
            payload = make_event_payload(evt_type.value, entity_type=category)
            event = WebhookEvent(**payload)
            assert event.type == evt_type

    def test_verification_challenge(self):
        challenge = VerificationChallenge(
            type="url_verification",
            challenge="abc123xyz",
        )
        assert challenge.challenge == "abc123xyz"


# ---------------------------------------------------------------------------
# EventDeduplicator Tests
# ---------------------------------------------------------------------------


class TestEventDeduplicator:
    """Test idempotency cache."""

    def test_first_event_not_duplicate(self):
        dedup = EventDeduplicator()
        assert not dedup.is_duplicate("evt-001")

    def test_second_event_is_duplicate(self):
        dedup = EventDeduplicator()
        dedup.is_duplicate("evt-001")
        assert dedup.is_duplicate("evt-001")

    def test_different_events_not_duplicate(self):
        dedup = EventDeduplicator()
        dedup.is_duplicate("evt-001")
        assert not dedup.is_duplicate("evt-002")

    def test_max_size_eviction(self):
        dedup = EventDeduplicator(max_size=3)
        dedup.is_duplicate("evt-001")
        dedup.is_duplicate("evt-002")
        dedup.is_duplicate("evt-003")
        dedup.is_duplicate("evt-004")  # Should evict evt-001
        assert not dedup.is_duplicate("evt-001")  # Evicted
        assert dedup.is_duplicate("evt-004")  # Still cached

    def test_ttl_expiration(self):
        dedup = EventDeduplicator(ttl_seconds=0)
        dedup.is_duplicate("evt-001")
        time.sleep(0.01)
        assert not dedup.is_duplicate("evt-001")  # Expired

    def test_size_tracking(self):
        dedup = EventDeduplicator()
        assert dedup.size == 0
        dedup.is_duplicate("evt-001")
        assert dedup.size == 1


# ---------------------------------------------------------------------------
# EventRouter Tests
# ---------------------------------------------------------------------------


class TestEventRouter:
    """Test event dispatch to category handlers."""

    @pytest.mark.asyncio
    async def test_dispatch_to_category_handler(self):
        router = EventRouter()
        handler = AsyncMock()
        router.register(EventCategory.PAGE, handler)

        event = WebhookEvent(**make_event_payload("page.created"))
        await router.dispatch(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_global_handler_runs_for_all(self):
        router = EventRouter()
        global_handler = AsyncMock()
        router.register_global(global_handler)

        for evt_type in ["page.created", "database.updated", "view.deleted"]:
            category = evt_type.split(".")[0]
            event = WebhookEvent(
                **make_event_payload(evt_type, entity_type=category)
            )
            await router.dispatch(event)

        assert global_handler.call_count == 3

    @pytest.mark.asyncio
    async def test_handler_error_doesnt_block_others(self):
        router = EventRouter()
        failing_handler = AsyncMock(side_effect=RuntimeError("boom"))
        passing_handler = AsyncMock()

        router.register(EventCategory.PAGE, failing_handler)
        router.register(EventCategory.PAGE, passing_handler)

        event = WebhookEvent(**make_event_payload("page.created"))
        executed = await router.dispatch(event)

        # Both attempted, passing handler still ran
        passing_handler.assert_called_once()


# ---------------------------------------------------------------------------
# HMAC Signature Tests
# ---------------------------------------------------------------------------


class TestHMACVerification:
    """Test webhook signature verification."""

    def test_valid_signature(self):
        body = b'{"test": true}'
        sig = make_signature(body)
        assert verify_webhook_signature(body, sig, WEBHOOK_SECRET)

    def test_invalid_signature_raises(self):
        body = b'{"test": true}'
        with pytest.raises(Exception):  # HTTPException
            verify_webhook_signature(body, "v1=invalid", WEBHOOK_SECRET)

    def test_missing_signature_raises(self):
        with pytest.raises(Exception):
            verify_webhook_signature(b"{}", None, WEBHOOK_SECRET)

    def test_stale_timestamp_raises(self):
        body = b'{"test": true}'
        sig = make_signature(body)
        stale_ts = str(int(time.time()) - 600)  # 10 min old

        with pytest.raises(Exception):
            verify_webhook_signature(
                body,
                sig,
                WEBHOOK_SECRET,
                timestamp_header=stale_ts,
                max_age_seconds=300,
            )


# ---------------------------------------------------------------------------
# WebhookResponse Model Tests
# ---------------------------------------------------------------------------


class TestWebhookResponse:
    def test_ok_response(self):
        resp = WebhookResponse(status="ok", event_id="evt-001", processed=True)
        assert resp.status == "ok"
        assert resp.processed is True

    def test_dedup_response(self):
        resp = WebhookResponse(
            status="ok",
            event_id="evt-001",
            processed=False,
            message="Duplicate",
        )
        assert not resp.processed
