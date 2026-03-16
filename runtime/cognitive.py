"""Cognitive state pipeline for AuDHD-adaptive skill execution.

Implements AGENT.md energy-adaptive routing and PROFILE.md cognitive contracts
as runtime-enforceable state rather than text instructions.

Resolves:
- A-2: PROFILE.md runtime integration (extends existing router)
- A-3: Cognitive state pipeline with energy-adaptive routing

F5/F6 fix: CognitiveState imported from schemas.py (canonical).
Duplicate dataclass removed. Low-energy pool corrected.
"""

from __future__ import annotations

from typing import Any

from runtime.schemas import (
    CognitiveState,
    EnergyLevel,
    TIER_ORDER,
    VALID_MODES,
)

# Re-export for backward compatibility
__all__ = [
    "CognitiveState", "EnergyLevel", "ENERGY_ROUTING", "TIER_ORDER",
    "VALID_MODES", "MODE_SIGNALS", "infer_mode", "filter_model_chain",
    "build_cognitive_preamble", "parse_cognitive_state",
    "get_routing", "get_max_tier_num", "tier_allowed", "get_output_mode",
]


# AGENT.md energy-adaptive routing table
ENERGY_ROUTING: dict[str, dict[str, Any]] = {
    "high": {
        "max_tier": "T5",
        "model_pool": "all",
        "behavior": "normal",
        "output_mode": "full",
    },
    "medium": {
        "max_tier": "T4",
        "model_pool": "all",
        "behavior": "standard",
        "output_mode": "standard",
    },
    "low": {
        "max_tier": "T2",
        "model_pool": ["gemini-2.5-flash", "o4-mini"],
        "behavior": "micro_steps",
        "output_mode": "minimal",
    },
    "crash": {
        "max_tier": "T1",
        "model_pool": [],
        "behavior": "save_state",
        "output_mode": "crash",
    },
}

MODE_SIGNALS: dict[str, list[str]] = {
    "osint": [
        "name", "phone", "address", "username", "email", "domain",
        "investigate", "research", "who is", "locate", "trace",
        "look into", "find",
    ],
    "troubleshoot": ["error", "crash", "exit code", "broken", "failure"],
    "draft": ["write", "draft", "compose"],
    "rewrite": ["fix", "edit", "rewrite", "update", "change"],
    "decide": ["should i", "compare", "which option", "which"],
    "design": ["build", "architect", "design"],
    "summarize": ["summarize", "condense", "tldr"],
    "review": ["review", "feedback", "check"],
    "chat": ["curious", "thinking", "wondering"],
}


# ---------------------------------------------------------------------------
# Standalone routing functions (operate on Pydantic CognitiveState)
# ---------------------------------------------------------------------------

def _energy_key(state: CognitiveState) -> str:
    """Convert EnergyLevel enum to ENERGY_ROUTING dict key."""
    if isinstance(state.energy_level, EnergyLevel):
        return state.energy_level.value
    return str(state.energy_level)


def get_routing(state: CognitiveState) -> dict[str, Any]:
    """Get AGENT.md energy routing config for current state."""
    return ENERGY_ROUTING[_energy_key(state)]


def get_max_tier_num(state: CognitiveState) -> int:
    """Max allowed tier number for current energy level."""
    return TIER_ORDER[get_routing(state)["max_tier"]]


def tier_allowed(state: CognitiveState) -> bool:
    """Check if current task tier is within energy-allowed range."""
    return state.task_tier_num <= get_max_tier_num(state)


def get_output_mode(state: CognitiveState) -> str:
    """Get output mode string for current energy level."""
    return get_routing(state)["output_mode"]


def infer_mode(input_text: str) -> str:
    """Infer PROFILE.md mode from natural language input."""
    lower = input_text.lower()
    for mode, signals in MODE_SIGNALS.items():
        for signal in signals:
            if signal in lower:
                return mode
    return "execute"


def filter_model_chain(
    model_chain: list[str],
    cognitive_state: CognitiveState,
    alias_map: dict[str, str],
) -> list[str]:
    """Filter model chain by AGENT.md energy-adaptive routing.

    High/Medium: all models. Low: gemini-2.5-flash + o4-mini only. Crash: empty.
    """
    pool = get_routing(cognitive_state)["model_pool"]
    if pool == "all":
        return model_chain
    if not pool:
        return []
    allowed = set(pool)
    filtered = [m for m in model_chain if m in allowed]
    if not filtered and model_chain:
        for candidate in reversed(model_chain):
            if candidate in allowed:
                return [candidate]
        return []
    return filtered


def build_cognitive_preamble(state: CognitiveState) -> str:
    """Build runtime cognitive state block for system prompt injection."""
    routing = get_routing(state)
    output_mode = routing["output_mode"]
    max_tier = routing["max_tier"]
    lines = [
        "## Active Cognitive State (injected by runtime/cognitive.py)",
        "",
        f"- **Energy level**: {_