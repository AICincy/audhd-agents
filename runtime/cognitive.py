"""Cognitive state pipeline for AuDHD-adaptive skill execution.

Implements AGENT.md energy-adaptive routing and PROFILE.md cognitive contracts
as runtime-enforceable state rather than text instructions.

Resolves:
- A-2: PROFILE.md runtime integration (extends existing router)
- A-3: Cognitive state pipeline with energy-adaptive routing

F5/F6 fix: CognitiveState imported from schemas.py (canonical).
Duplicate dataclass removed. Low-energy pool corrected.
F7 fix: filter_model_chain now resolves aliases before pool comparison.
F8 fix: infer_mode uses word-boundary regex; rewrite before draft;
OSINT signals scoped (removed generic 'name', 'find', 'domain').
"""

from __future__ import annotations

import re
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

# Mode signal keywords (order matters: rewrite before draft to prevent
# "write" in "rewrite" false match).  OSINT scoped to investigative
# terms only -- generic "name", "find", "domain" removed (F8).
MODE_SIGNALS: dict[str, list[str]] = {
    "osint": [
        "phone", "address", "username", "email",
        "investigate", "research", "who is", "locate", "trace",
        "look into",
    ],
    "troubleshoot": ["error", "crash", "exit code", "broken", "failure"],
    "rewrite": ["fix", "edit", "rewrite", "update", "change"],
    "draft": ["write", "draft", "compose"],
    "decide": ["should i", "compare", "which option", "which"],
    "design": ["build", "architect", "design"],
    "summarize": ["summarize", "condense", "tldr"],
    "review": ["review", "feedback", "check"],
    "chat": ["curious", "thinking", "wondering"],
}

# Pre-compiled word-boundary patterns for mode inference (F8)
_MODE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    mode: [re.compile(rf"\b{re.escape(sig)}\b", re.IGNORECASE) for sig in sigs]
    for mode, sigs in MODE_SIGNALS.items()
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
    """Infer PROFILE.md mode from natural language input.

    Uses pre-compiled word-boundary regex to prevent substring false
    matches (e.g. 'write' inside 'rewrite').  F8 fix.
    """
    for mode, patterns in _MODE_PATTERNS.items():
        for pat in patterns:
            if pat.search(input_text):
                return mode
    return "execute"


def _matches_pool(alias: str, allowed: set[str], alias_map: dict[str, str]) -> bool:
    """Check if a model alias matches any entry in the allowed pool.

    Resolves alias to full qualified name via alias_map, then checks if any
    pool entry is a substring of the resolved name (e.g. 'o4-mini' in
    'openai/o4-mini'). Falls back to direct membership check.
    """
    # Direct match first (no alias resolution needed)
    if alias in allowed:
        return True
    # Resolve alias to full qualified name
    resolved = alias_map.get(alias, alias)
    if resolved in allowed:
        return True
    # Substring match: pool entries like "o4-mini" match "openai/o4-mini"
    return any(pool_entry in resolved for pool_entry in allowed)


def filter_model_chain(
    model_chain: list[str],
    cognitive_state: CognitiveState,
    alias_map: dict[str, str],
) -> list[str]:
    """Filter model chain by AGENT.md energy-adaptive routing.

    High/Medium: all models. Low: gemini-2.5-flash + o4-mini only. Crash: empty.
    Resolves aliases via alias_map before comparing against the energy pool.
    """
    pool = get_routing(cognitive_state)["model_pool"]
    if pool == "all":
        return model_chain
    if not pool:
        return []
    allowed = set(pool)
    filtered = [m for m in model_chain if _matches_pool(m, allowed, alias_map)]
    if not filtered and model_chain:
        # Fallback: try reversed chain for best available match
        for candidate in reversed(model_chain):
            if _matches_pool(candidate, allowed, alias_map):
                return [candidate]
        return []
    return filtered


def build_cognitive_preamble(state: CognitiveState) -> str:
    """Build runtime cognitive state block for system prompt injection."""
    routing = get_routing(state)
    output_mode = routing["output_mode"]
    max_tier = routing["max_tier"]
    e_key = _energy_key(state)
    attention = state.attention_state.value if hasattr(state.attention_state, "value") else str(state.attention_state)
    session = state.session_context.value if hasattr(state.session_context, "value") else str(state.session_context)

    lines = [
        "## Active Cognitive State (injected by runtime/cognitive.py)",
        "",
        f"- **Energy level**: {e_key}",
        f"- **Output mode**: {output_mode}",
        f"- **Max tier**: {max_tier}",
        f"- **Active mode**: {state.active_mode}",
        f"- **Attention**: {attention}",
        f"- **Session**: {session}",
        f"- **Context switches**: {state.context_switches}",
    ]

    if state.active_thread:
        lines.append(f"- **Active thread**: {state.active_thread}")

    if state.is_crash():
        lines.extend([
            "",
            "**CRASH MODE ACTIVE**: No model calls. Save state checkpoint only.",
        ])

    if state.needs_resume():
        lines.extend([
            "",
            f"**RESUME FROM**: {state.resume_from}",
        ])

    return "\n".join(lines)


def parse_cognitive_state(data: dict[str, Any] | None = None) -> CognitiveState:
    """Parse cognitive state from request data with safe defaults."""
    if not data:
        return CognitiveState()
    try:
        return CognitiveState(**data)
    except (ValueError, TypeError):
        return CognitiveState()
