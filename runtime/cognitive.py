"""Cognitive state pipeline for AuDHD-adaptive skill execution.

Implements AGENT.md energy-adaptive routing and PROFILE.md cognitive contracts
as runtime-enforceable state rather than text instructions.

Resolves:
- A-2: PROFILE.md runtime integration (extends existing router)
- A-3: Cognitive state pipeline with energy-adaptive routing
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
        "model_pool": ["G-PRO", "G-PRO31", "G-FLA31", "O-O4M"],
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

TIER_ORDER: dict[str, int] = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}

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
    """Runtime cognitive state from PROFILE.md and AGENT.md contracts."""

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
        return ENERGY_ROUTING[self.energy_level]

    @property
    def max_tier_num(self) -> int:
        return TIER_ORDER[self.routing["max_tier"]]

    @property
    def task_tier_num(self) -> int:
        return TIER_ORDER[self.task_tier]

    @property
    def tier_allowed(self) -> bool:
        return self.task_tier_num <= self.max_tier_num

    @property
    def is_crash(self) -> bool:
        return self.energy_level == "crash"

    @property
    def output_mode(self) -> str:
        return self.routing["output_mode"]


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

    High/Medium: all models. Low: Sonnet + Gemini only. Crash: empty.
    """
    pool = cognitive_state.routing["model_pool"]
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
            f"- **WARNING**: {state.context_switches} context switches. "
            "Monotropism contract: minimize further switching."
        )
    if not state.tier_allowed:
        lines.append(
            f"- **TIER BLOCKED**: {state.task_tier} exceeds max "
            f"{state.routing['max_tier']}. Defer or downgrade."
        )
    if state.is_crash:
        lines.extend([
            "",
            "**CRASH MODE ACTIVE**: Output only state summary + reassurance.",
            "No new analysis. No deliverables. No questions.",
        ])
    return "\n".join(lines)


def parse_cognitive_state(options: dict[str, Any]) -> CognitiveState:
    """Extract cognitive state from request options (nested or flat)."""
    cs = options.get("cognitive_state", {})
    if isinstance(cs, dict) and cs:
        return CognitiveState(
            energy_level=cs.get("energy_level", "medium"),
            active_mode=cs.get("active_mode", ""),
            task_tier=cs.get("task_tier", "T3"),
            active_thread=cs.get("active_thread", ""),
            context_switches=cs.get("context_switches", 0),
        )
    return CognitiveState(
        energy_level=options.get("energy_level", "medium"),
        active_mode=options.get("active_mode", ""),
        task_tier=options.get("task_tier", "T3"),
        active_thread=options.get("active_thread", ""),
        context_switches=options.get("context_switches", 0),
    )
