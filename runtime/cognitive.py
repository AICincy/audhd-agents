"""Cognitive state pipeline for AuDHD-adaptive skill execution.

Implements AGENT.md energy-adaptive routing and PROFILE.md cognitive contracts
as runtime-enforceable state rather than text instructions.

This module is the runtime mechanism for A-2 (PROFILE.md loading) and
A-3 (cognitive state pipeline). It replaces the dead-code pattern of
"Load PROFILE.md before processing" with actual state that models branch on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# AGENT.md energy-adaptive routing table (Section: Energy-Adaptive Routing)
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
        "model_pool": ["C-SN46", "C-SN45", "G-PRO"],
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

# AGENT.md tier numeric mapping (Section: Task Classification)
TIER_ORDER: dict[str, int] = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}

# PROFILE.md mode routing table (Section: Mode Routing)
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


@dataclass
class CognitiveState:
    """Runtime cognitive state derived from PROFILE.md and AGENT.md contracts.

    This is the central data structure that replaces static text instructions
    with actual state that the runtime and models can branch on.

    Attributes:
        energy_level: Operator energy from AGENT.md energy-adaptive routing.
        active_mode: Inferred from PROFILE.md mode routing table.
        task_tier: AGENT.md complexity classification (T1-T5).
        active_thread: Current monotropic focus thread.
        context_switches: Number of topic switches in session.
    """

    energy_level: str = "medium"
    active_mode: str = "execute"
    task_tier: str = "T3"
    active_thread: str = ""
    context_switches: int = 0

    def __post_init__(self) -> None:
        if self.energy_level not in ENERGY_ROUTING:
            self.energy_level = "medium"
        if self.task_tier not in TIER_ORDER:
            self.task_tier = "T3"
        valid_modes = {
            "osint", "troubleshoot", "draft", "rewrite", "decide",
            "design", "summarize", "review", "chat", "execute",
        }
        if self.active_mode not in valid_modes:
            self.active_mode = "execute"

    @property
    def routing(self) -> dict[str, Any]:
        """Get AGENT.md energy-adaptive routing config for current state."""
        return ENERGY_ROUTING[self.energy_level]

    @property
    def max_tier_num(self) -> int:
        """Numeric max tier allowed by current energy level."""
        return TIER_ORDER[self.routing["max_tier"]]

    @property
    def task_tier_num(self) -> int:
        """Numeric value of requested task tier."""
        return TIER_ORDER[self.task_tier]

    @property
    def tier_allowed(self) -> bool:
        """Whether current task tier is allowed at current energy level."""
        return self.task_tier_num <= self.max_tier_num

    @property
    def is_crash(self) -> bool:
        """Whether operator is in crash energy state."""
        return self.energy_level == "crash"

    @property
    def output_mode(self) -> str:
        """Output density mode from AGENT.md routing."""
        return self.routing["output_mode"]


def infer_mode(input_text: str) -> str:
    """Infer PROFILE.md mode from natural language input.

    Scans input for signal words from the mode routing table.
    Returns the first matching mode, or 'execute' as default.
    """
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
    """Filter model chain by energy-adaptive routing rules from AGENT.md.

    High/Medium energy: all models allowed.
    Low energy: only Sonnet + Gemini (fast, budget models).
    Crash energy: empty chain (no new tasks).

    Args:
        model_chain: Ordered list of model aliases to try.
        cognitive_state: Current cognitive state.
        alias_map: Alias to provider/model mapping from config.yaml.

    Returns:
        Filtered model chain respecting energy constraints.
    """
    pool = cognitive_state.routing["model_pool"]

    if pool == "all":
        return model_chain

    if not pool:  # crash mode: no new tasks
        return []

    # Filter to energy-allowed aliases
    allowed = set(pool)
    filtered = [m for m in model_chain if m in allowed]

    # If filtering removed everything, keep the last fallback
    # (graceful degradation over hard failure)
    if not filtered and model_chain:
        for candidate in reversed(model_chain):
            if candidate in allowed:
                return [candidate]
        # No allowed model in chain at all: return empty
        return []

    return filtered


def build_cognitive_preamble(state: CognitiveState) -> str:
    """Build runtime cognitive state block for injection into system prompt.

    This replaces the static 'Load PROFILE.md before processing' text
    instruction with actual state that the model can branch on.
    The preamble is injected BEFORE the skill-specific prompt.

    Args:
        state: Current cognitive state.

    Returns:
        Markdown block with active cognitive state for prompt injection.
    """
    lines = [
        "## Active Cognitive State (injected by runtime/cognitive.py)",
        "",
        f"- **Energy level**: {state.energy_level}",
        f"- **Mode**: {state.active_mode}",
        f"- **Task tier**: {state.task_tier} (max allowed: {state.routing['max_tier']})",
        f"- **Output mode**: {state.output_mode}",
    ]

    if state.active_thread:
        lines.append(f"- **Active thread**: {state.active_thread}")

    if state.context_switches > 2:
        lines.append(
            f"- **WARNING**: {state.context_switches} context switches detected. "
            "Monotropism contract: minimize further switching. Present one result at a time."
        )

    if not state.tier_allowed:
        lines.append(
            f"- **TIER BLOCKED**: Task tier {state.task_tier} exceeds energy-allowed "
            f"max {state.routing['max_tier']}. Defer to next high-energy window or downgrade scope."
        )

    if state.is_crash:
        lines.extend([
            "",
            "**CRASH MODE ACTIVE**: Output only state summary and reassurance.",
            "No new analysis. No deliverables. No questions.",
            'Format: "Everything is saved. Nothing is urgent. '
            'Here is where you left off: [context]. Come back when ready."',
        ])

    return "\n".join(lines)


def parse_cognitive_state(options: dict[str, Any]) -> CognitiveState:
    """Extract cognitive state from skill request options.

    Supports both nested and flat option formats:
      - Nested: {"cognitive_state": {"energy_level": "low", ...}}
      - Flat: {"energy_level": "low", "task_tier": "T2", ...}

    Args:
        options: Request options dict from SkillRequest.

    Returns:
        Parsed CognitiveState with validated fields.
    """
    cs = options.get("cognitive_state", {})
    if isinstance(cs, dict) and cs:
        return CognitiveState(
            energy_level=cs.get("energy_level", "medium"),
            active_mode=cs.get("active_mode", ""),
            task_tier=cs.get("task_tier", "T3"),
            active_thread=cs.get("active_thread", ""),
            context_switches=cs.get("context_switches", 0),
        )

    # Flat format fallback
    return CognitiveState(
        energy_level=options.get("energy_level", "medium"),
        active_mode=options.get("active_mode", ""),
        task_tier=options.get("task_tier", "T3"),
        active_thread=options.get("active_thread", ""),
        context_switches=options.get("context_switches", 0),
    )
