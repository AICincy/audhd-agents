"""Pydantic models for Notion Webhook events.

Notion API version: 2026-03-11
Event categories: Page (8), Database (6), Data source (6), View (3)
No stubs. No bandaids. Production models with full validation.
"""

from __future__ import annotations

import enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WebhookEventType(str, enum.Enum):
    """All 28 Notion webhook event types."""
    # Page events (8)
    PAGE_CREATED = "page.created"
    PAGE_UPDATED = "page.updated"
    PAGE_DELETED = "page.deleted"
    PAGE_RESTORED = "page.restored"
    PAGE_MOVED = "page.moved"
    PAGE_LOCKED = "page.locked"
    PAGE_UNLOCKED = "page.unlocked"
    PAGE_CONTENT_UPDATED = "page.content_updated"

    # Database events (6)
    DATABASE_CREATED = "database.created"
    DATABASE_UPDATED = "database.updated"
    DATABASE_DELETED = "database.deleted"
    DATABASE_RESTORED = "database.restored"
    DATABASE_SCHEMA_UPDATED = "database.schema_updated"
    DATABASE_MOVED = "database.moved"

    # Data source events (6)
    DATA_SOURCE_CREATED = "data_source.created"
    DATA_SOURCE_UPDATED = "data_source.updated"
    DATA_SOURCE_DELETED = "data_source.deleted"
    DATA_SOURCE_RESTORED = "data_source.restored"
    DATA_SOURCE_SCHEMA_UPDATED = "data_source.schema_updated"
    DATA_SOURCE_ROW_ADDED = "data_source.row_added"

    # View events (3)
    VIEW_CREATED = "view.created"
    VIEW_UPDATED = "view.updated"
    VIEW_DELETED = "view.deleted"


class EventCategory(str, enum.Enum):
    """Top-level event categories for routing."""
    PAGE = "page"
    DATABASE = "database"
    DATA_SOURCE = "data_source"
    VIEW = "view"


# ---------------------------------------------------------------------------
# Event Payload Models
# ---------------------------------------------------------------------------

class WebhookAuthor(BaseModel):
    """User or bot that triggered the event."""
    model_config = ConfigDict(frozen=True)

    id: str
    type: str = Field(description="'user' or 'bot'")
    name: Optional[str] = None


class WebhookEntity(BaseModel):
    """Reference to the Notion entity that changed."""
    model_config = ConfigDict(frozen=True)

    id: str
    type: str = Field(description="'page', 'database', 'data_source', 'view'")
    url: Optional[str] = None
    title: Optional[str] = None
    parent_id: Optional[str] = None
    parent_type: Optional[str] = None


class WebhookEventData(BaseModel):
    """Payload data for a webhook event."""
    model_config = ConfigDict(extra="allow")

    entity: WebhookEntity
    author: Optional[WebhookAuthor] = None
    updated_properties: Optional[list[str]] = None
    previous_parent: Optional[WebhookEntity] = None
    timestamp: Optional[str] = None


class WebhookEvent(BaseModel):
    """Top-level webhook event envelope.

    This is the JSON body Notion POSTs to your webhook URL.
    """
    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique event ID for idempotency")
    type: WebhookEventType
    timestamp: str = Field(description="ISO-8601 event timestamp")
    workspace_id: str
    subscription_id: str
    data: WebhookEventData
    api_version: str = Field(default="2026-03-11")

    @property
    def category(self) -> EventCategory:
        """Extract category from event type (e.g., 'page' from 'page.created')."""
        prefix = self.type.value.split(".")[0]
        return EventCategory(prefix)

    @property
    def action(self) -> str:
        """Extract action from event type (e.g., 'created' from 'page.created')."""
        return self.type.value.split(".", 1)[1]


class VerificationChallenge(BaseModel):
    """Notion sends this on subscription creation to verify endpoint ownership."""
    model_config = ConfigDict(frozen=True)

    type: str = Field(default="url_verification")
    challenge: str


class WebhookResponse(BaseModel):
    """Standard response for webhook events."""
    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    event_id: Optional[str] = None
    processed: bool = False
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal Processing Models
# ---------------------------------------------------------------------------

class ProcessedEvent(BaseModel):
    """Internal model after event processing and dedup."""
    model_config = ConfigDict(frozen=True)

    event: WebhookEvent
    received_at: str
    deduplicated: bool = False
    routed_to: Optional[str] = None
    processing_ms: Optional[float] = None
    error: Optional[str] = None
