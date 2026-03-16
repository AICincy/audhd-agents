"""Bridge from webhook events to the cognitive skill pipeline.

Connects EventRouter handlers to SkillRouter.execute() so that
incoming Notion events trigger real skill execution.

Architecture:
    WebhookEvent -> map_event_to_skill() -> SkillRequest -> SkillRouter.execute()

Initialized during app lifespan via init_bridge(router).
Handlers call dispatch_event() which is a no-op until init completes.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from runtime.schemas import CognitiveState, EnergyLevel
from runtime.webhook_schemas import WebhookEvent, EventCategory

logger = logging.getLogger("audhd_agents.pipeline_bridge")

# Module-level router reference, set during app lifespan
_router = None
_skill_index: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Initialization (called from app.py lifespan)
# ---------------------------------------------------------------------------

def init_bridge(router: Any, skill_index: dict[str, Any]) -> None:
    """Store router reference for handler use. Called once at startup."""
    global _router, _skill_index
    _router = router
    _skill_index = skill_index
    logger.info(json.dumps({
        "event": "pipeline_bridge_initialized",
        "skill_count": len(skill_index),
    }))


def is_ready() -> bool:
    """True if bridge has a router and skills loaded."""
    return _router is not None and bool(_skill_index)


# ---------------------------------------------------------------------------
# Event-to-skill mapping
# ---------------------------------------------------------------------------

# Maps (category, action) to skill_id.
# None means no skill trigger, just log.
_EVENT_SKILL_MAP: dict[tuple[str, str], Optional[str]] = {
    # Page lifecycle
    ("page", "created"): "decompose",
    ("page", "updated"): "quality-gate",
    ("page", "content_updated"): "verify",
    ("page", "deleted"): None,
    ("page", "restored"): None,
    ("page", "moved"): None,
    ("page", "locked"): None,
    ("page", "unlocked"): None,

    # Database lifecycle
    ("database", "created"): None,
    ("database", "updated"): None,
    ("database", "deleted"): None,
    ("database", "restored"): None,
    ("database", "schema_updated"): "system-audit",
    ("database", "moved"): None,

    # Data source lifecycle
    ("data_source", "created"): None,
    ("data_source", "updated"): None,
    ("data_source", "deleted"): None,
    ("data_source", "restored"): None,
    ("data_source", "schema_updated"): "system-audit",
    ("data_source", "row_added"): "decompose",

    # View lifecycle
    ("view", "created"): None,
    ("view", "updated"): None,
    ("view", "deleted"): None,
}


def map_event_to_skill(event: WebhookEvent) -> Optional[str]:
    """Determine which skill (if any) should handle this event."""
    key = (event.category.value, event.action)
    skill_id = _EVENT_SKILL_MAP.get(key)

    # Validate skill exists in index
    if skill_id and skill_id not in _skill_index:
        logger.warning(json.dumps({
            "event": "skill_not_in_index",
            "skill_id": skill_id,
            "event_type": event.type.value,
            "available_skills": list(_skill_index.keys())[:10],
        }))
        return None

    return skill_id


# ---------------------------------------------------------------------------
# Cognitive state factory
# ---------------------------------------------------------------------------

def build_cognitive_state_for_event(event: WebhookEvent) -> CognitiveState:
    """Build appropriate cognitive state based on event context.

    Webhook-triggered work defaults to medium energy (autonomous background).
    Schema changes get low energy (lightweight audit).
    """
    action = event.action

    if action in ("deleted", "restored", "locked", "unlocked", "moved"):
        energy = EnergyLevel.LOW
    elif action in ("schema_updated",):
        energy = EnergyLevel.LOW
    elif action in ("created", "content_updated", "row_added"):
        energy = EnergyLevel.MEDIUM
    else:
        energy = EnergyLevel.MEDIUM

    return CognitiveState(
        energy_level=energy,
        attention_state="focused",
        session_context="new",
    )


# ---------------------------------------------------------------------------
# Input text builder
# ---------------------------------------------------------------------------

def build_input_text(event: WebhookEvent) -> str:
    """Build skill input text from webhook event data."""
    entity = event.data.entity
    parts = [
        f"Event: {event.type.value}",
        f"Entity: {entity.type} ({entity.id})",
    ]

    if entity.title:
        parts.append(f"Title: {entity.title}")

    if entity.url:
        parts.append(f"URL: {entity.url}")

    if event.data.updated_properties:
        parts.append(f"Updated properties: {', '.join(event.data.updated_properties)}")

    if event.data.author:
        parts.append(f"Author: {event.data.author.name or event.data.author.id} ({event.data.author.type})")

    if entity.parent_id:
        parts.append(f"Parent: {entity.parent_type} ({entity.parent_id})")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Dispatch (called from webhook handlers)
# ---------------------------------------------------------------------------

async def dispatch_event(event: WebhookEvent) -> Optional[dict[str, Any]]:
    """Route a webhook event to the cognitive pipeline.

    Returns:
        Skill execution result dict, or None if no skill mapped / bridge not ready.
    """
    if not is_ready():
        logger.warning(json.dumps({
            "event": "bridge_not_ready",
            "event_type": event.type.value,
            "event_id": event.id,
        }))
        return None

    skill_id = map_event_to_skill(event)
    if not skill_id:
        logger.debug(json.dumps({
            "event": "no_skill_mapped",
            "event_type": event.type.value,
        }))
        return None

    # Build request components
    cognitive_state = build_cognitive_state_for_event(event)
    input_text = build_input_text(event)

    logger.info(json.dumps({
        "event": "dispatching_to_skill",
        "skill_id": skill_id,
        "event_type": event.type.value,
        "entity_id": event.data.entity.id,
        "energy_level": cognitive_state.energy_level.value,
    }))

    try:
        # Import here to avoid circular imports
        from adapters.base import SkillRequest

        skill_request = SkillRequest(
            skill_id=skill_id,
            input_text=input_text,
            options={"source": "webhook", "event_id": event.id},
        )

        result = await _router.execute(
            skill_request,
            cognitive_state_override=cognitive_state,
        )

        logger.info(json.dumps({
            "event": "skill_execution_complete",
            "skill_id": skill_id,
            "event_id": event.id,
            "model_used": getattr(result, "model_used", None),
            "latency_ms": getattr(result, "latency_ms", None),
        }))

        return {
            "skill_id": skill_id,
            "output": getattr(result, "output", {}),
            "model_used": getattr(result, "model_used", None),
            "latency_ms": getattr(result, "latency_ms", None),
        }

    except Exception as exc:
        logger.error(json.dumps({
            "event": "skill_execution_failed",
            "skill_id": skill_id,
            "event_id": event.id,
            "error": str(exc),
            "error_class": exc.__class__.__name__,
        }))
        return {
            "skill_id": skill_id,
            "error": str(exc),
            "error_class": exc.__class__.__name__,
        }
