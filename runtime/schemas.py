"""runtime/schemas.py

Pydantic models for the AuDHD Cognitive Swarm /execute endpoint.
Defines cognitive state as a first-class request parameter.

Design contract (from PROFILE.md + AGENT.md):
- energy_level controls model selection, output density, and crash protection
- attention_state informs monotropism guards
- session_context enables "Where Was I?" protocol
- crash mode short-circuits before any model call

F1/F5 fix: CognitiveState is the single canonical contract.
runtime/cognitive.py re-exports for backward compatibility.
audhd-skills/_base/schema_base.json mirrors the JSON Schema surface.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

# ---------------------------------------------------------------------------
# Constants (shared with cognitive.py via import)
# ---------------------------------------------------------------------------

TIER_ORDER: dict[str, int] = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}

VALID_MODES: set[str] = {
    "osint", "troubleshoot", "draft", "rewrite", "decide",
    "design", "summarize", "review", "chat", "execute",
}

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
# Cognitive State Model (canonical single source of truth)
# ---------------------------------------------------------------------------

class CognitiveState(BaseModel):
    """Unified cognitive context for the AuDHD architecture.

    Cognitive co-processor state. Every skill adapts to current capacity.

    Canonical contract: runtime/schemas.py owns this model.
    runtime/cognitive.py re-exports for backward compatibility.
    audhd-skills/_base/schema_base.json mirrors the JSON Schema surface.
    """
    model_config = ConfigDict(frozen=True)

    energy_level: EnergyLevel = Field(
        default=EnergyLevel.MEDIUM,
        description="Current energy/capacity level. Controls model selection and output density.",
    )
    attention_state: AttentionState = Field(
        default=AttentionState.FOCUSED,
        description="Current attention mode. Controls monotropism guard strictness.",
    )
    session_context: SessionContext = Field(
        default=SessionContext.NEW,
        description="Session continuity state. Controls Where Was I protocol.",
    )
    resume_from: Optional[str] = Field(
        default=None,
        description="Checkpoint ID to resume from. Only used when session_context is RESUMED or INTERRUPTED.",
    )
    active_mode: str = Field(
        default="execute",
        description="Inferred PROFILE.md mode (execute, osint, troubleshoot, etc.).",
    )
    task_tier: str = Field(
        default="T3",
        description="Task complexity tier (T1-T5). Controls verification requirements.",
    )
    active_thread: str = Field(
        default="",
        description="Current monotropism thread identifier.",
    )
    context_switches: int = Field(
        default=0,
        ge=0,
        description="Number of context switches in session. Triggers monotropism guard at >2.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracing and resume context.",
    )
    resume_context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional. State from previous execution for continuity.",
    )

    @field_validator("active_mode")
    @classmethod
    def validate_active_mode(cls, v: str) -> str:
        if v not in VALID_MODES:
            return "execute"
        return v

    @field_validator("task_tier")
    @classmethod
    def validate_task_tier(cls, v: str) -> str:
        if v not in TIER_ORDER:
            return "T3"
        return v

    @property
    def task_tier_num(self) -> int:
        """Numeric tier for comparison."""
        return TIER_ORDER.get(self.task_tier, 3)

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
    model_config = ConfigDict(frozen=True)

    skill_id: Optional[str] = Field(
        default=None,
        description="Skill directory name, e.g. 'engineering-code-reviewer'. Optional for capability routing.",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    input_text: str = Field(
        ...,
        description="Primary input text for the skill",
        min_length=1,
        max_length=1048576,
    )
    cognitive_state: CognitiveState = Field(
        default_factory=CognitiveState,
        description="Cognitive context. Defaults to medium energy, focused, new session.",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Skill-specific options passthrough",
    )
    model_override: Optional[str] = Field(
        default=None,
        description="Force a specific model ID. Bypasses energy routing.",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request ID for tracing. Auto-generated if omitted.",
    )

    @model_validator(mode='after')
    def validate_session_resume(self) -> 'ExecuteRequest':
        if self.cognitive_state.needs_resume() and not self.cognitive_state.resume_from:
            raise ValueError("session_context RESUMED or INTERRUPTED requires a resume_from checkpoint.")
        if not self.cognitive_state.needs_resume() and self.cognitive_state.resume_from:
            raise ValueError("resume_from checkpoint provided but session_context is NEW.")
        return self


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class CognitiveCompliance(BaseModel):
    """Output validation results against the cognitive contract."""
    model_config = ConfigDict(frozen=True)

    compliant: bool = True
    violations: list[str] = Field(default_factory=list)


class CrashStateResponse(BaseModel):
    """Response shape for crash mode. No model was called."""
    model_config = ConfigDict(frozen=True)

    checkpoint: str = Field(
        ...,
        description="What was in progress when crash mode activated",
    )
    resume_action: str = Field(
        ...,
        description="Single action to take when energy recovers",
    )
    message: str = Field(
        default="Checkpoint saved. One action when ready.",
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
    model_config = ConfigDict(frozen=True)

    output: dict[str, Any] = Field(
        default_factory=dict,
        description="Skill output. Empty dict in crash mode.",
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Model ID that processed the request. None in crash mode.",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Provider that handled the request. None in crash mode.",
    )
    energy_level: EnergyLevel = Field(
        description="Echo of the energy level used for routing",
    )
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    cached: bool = False
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hooks_executed: list[str] = Field(
        default_factory=list,
        description="Skill hooks that ran (e.g. ['quality-gate', 'verify'])",
    )
    cognitive_compliance: CognitiveCompliance = Field(
        default_factory=CognitiveCompliance,
    )
    crash_state: Optional[CrashStateResponse] = Field(
        default=None,
        description="Populated only when energy_level is CRASH",
    )

    @model_validator(mode='after')
    def validate_crash_state(self) -> 'ExecuteResponse':
        if self.energy_level == EnergyLevel.CRASH and not self.crash_state:
            raise ValueError("crash_state must be populated when energy_level is CRASH.")
        if self.energy_level != EnergyLevel.CRASH and self.crash_state:
            raise ValueError("crash_state cannot be populated unless energy_level is CRASH.")
        return self
