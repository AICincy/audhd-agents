"""runtime/schemas.py

Pydantic models for the AuDHD Cognitive Swarm /execute endpoint.
Defines cognitive state as a first-class request parameter.

Design contract (from PROFILE.md + AGENT.md):
- energy_level controls model selection, output density, and crash protection
- attention_state informs monotropism guards
- session_context enables "Where Was I?" protocol
- crash mode short-circuits before any model call
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Cognitive State Enums
# ---------------------------------------------------------------------------

class EnergyLevel(str, Enum):
    """Maps to AGENT.md Energy-Adaptive Routing matrix.
    
    HIGH   -> full model pool, full output
    MEDIUM -> mid-tier models, standard output
    LOW    -> fastest models only, single micro-action
    CRASH  -> NO model call. Save state. Stop.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRASH = "crash"


class AttentionState(str, Enum):
    """Monotropism signal from PROFILE.md.
    
    FOCUSED       -> single-thread enforcement strict
    DIFFUSE       -> allow broader context gathering
    TRANSITIONING -> announce topic shift before executing
    """
    FOCUSED = "focused"
    DIFFUSE = "diffuse"
    TRANSITIONING = "transitioning"


class SessionContext(str, Enum):
    """Where Was I? protocol from AGENT.md.
    
    NEW         -> fresh session, no prior state
    RESUMED     -> returning after break, load checkpoint
    INTERRUPTED -> unexpected break, recover gracefully
    """
    NEW = "new"
    RESUMED = "resumed"
    INTERRUPTED = "interrupted"


# ---------------------------------------------------------------------------
# Cognitive State Model
# ---------------------------------------------------------------------------

class CognitiveState(BaseModel):
    """Cognitive context passed with every /execute request.
    
    This is the nervous system of the AuDHD architecture.
    Without it, skills are generic LLM templates.
    With it, every skill adapts to the user's current capacity.
    """
    energy_level: EnergyLevel = Field(
        default=EnergyLevel.MEDIUM,
        description="Current energy/capacity level. Controls model selection and output density."
    )
    attention_state: AttentionState = Field(
        default=AttentionState.FOCUSED,
        description="Current attention mode. Controls monotropism guard strictness."
    )
    session_context: SessionContext = Field(
        default=SessionContext.NEW,
        description="Session continuity state. Controls Where Was I protocol."
    )
    resume_from: Optional[str] = Field(
        default=None,
        description="Checkpoint ID to resume from. Only used when session_context is RESUMED or INTERRUPTED."
    )

    def is_crash(self) -> bool:
        """Crash mode = no model call. Save state and stop."""
        return self.energy_level == EnergyLevel.CRASH

    def needs_resume(self) -> bool:
        """Check if this request needs the Where Was I protocol."""
        return self.session_context in (SessionContext.RESUMED, SessionContext.INTERRUPTED)


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    """POST /execute request body.
    
    Changes from prior version:
    - ADDED: cognitive_state (CognitiveState) with sensible defaults
    - ADDED: request_id auto-generation if not provided
    - KEPT: skill_id, input_text, options, model_override (backward compatible)
    """
    skill_id: str = Field(
        ...,
        description="Skill directory name, e.g. 'engineering-code-reviewer'"
    )
    input_text: str = Field(
        ...,
        description="Primary input text for the skill"
    )
    cognitive_state: CognitiveState = Field(
        default_factory=CognitiveState,
        description="Cognitive context. Defaults to medium energy, focused, new session."
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Skill-specific options passthrough"
    )
    model_override: Optional[str] = Field(
        default=None,
        description="Force a specific model ID. Bypasses energy routing."
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request ID for tracing. Auto-generated if omitted."
    )


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class CognitiveCompliance(BaseModel):
    """Output validation results against the cognitive contract."""
    compliant: bool = True
    violations: list[str] = Field(default_factory=list)


class CrashStateResponse(BaseModel):
    """Response shape for crash mode. No model was called."""
    checkpoint: str = Field(
        ...,
        description="What was in progress when crash mode activated"
    )
    resume_action: str = Field(
        ...,
        description="Single action to take when energy recovers"
    )
    message: str = Field(
        default="State saved. Nothing is urgent. Resume when ready."
    )


class ExecuteResponse(BaseModel):
    """POST /execute response body.
    
    Changes from prior version:
    - ADDED: cognitive_compliance (validation results)
    - ADDED: crash_state (populated only in crash mode)
    - ADDED: energy_level echo (confirms what routing used)
    - ADDED: hooks_executed (which sk_hooks ran)
    - KEPT: output, model_used, provider, tokens, latency, request_id
    """
    output: dict[str, Any] = Field(
        default_factory=dict,
        description="Skill output. Empty dict in crash mode."
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Model ID that processed the request. None in crash mode."
    )
    provider: Optional[str] = Field(
        default=None,
        description="Provider that handled the request. None in crash mode."
    )
    energy_level: EnergyLevel = Field(
        description="Echo of the energy level used for routing"
    )
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    request_id: str = ""
    hooks_executed: list[str] = Field(
        default_factory=list,
        description="sk_hooks that ran (e.g. ['SK-GATE', 'SK-VERIFY'])"
    )
    cognitive_compliance: CognitiveCompliance = Field(
        default_factory=CognitiveCompliance
    )
    crash_state: Optional[CrashStateResponse] = Field(
        default=None,
        description="Populated only when energy_level is CRASH"
    )
