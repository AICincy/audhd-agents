"""Output validation against PROFILE.md cognitive contract. Resolves A-6.

Post-processing: flags violations transparently, does NOT modify output
(per honesty protocol: explicit over implicit).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Validation result with violations and warnings."""
    passed: bool = True
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_violation(self, rule: str, detail: str) -> None:
        self.passed = False
        self.violations.append(f"[{rule}] {detail}")

    def add_warning(self, rule: str, detail: str) -> None:
        self.warnings.append(f"[{rule}] {detail}")


EM_DASH_PATTERN = re.compile(r"[\u2014\u2013\u2012]")

FILLER_PHRASES = [
    "as an ai", "i'd be happy to", "great question", "that's a great",
    "let me help you", "absolutely!", "of course!", "sure thing",
    "no problem", "here's what i think", "have you tried",
    "have you considered", "i hope this helps", "feel free to",
]

MOTIVATION_PHRASES = [
    "you've got this", "keep going", "great job", "well done",
    "amazing work", "you're doing great", "stay positive",
    "believe in yourself", "proud of you", "keep it up",
]


def validate_output(
    output_text: str,
    active_mode: str = "execute",
    energy_level: str = "medium",
    task_tier: str = "T3",
) -> ValidationResult:
    """Validate model output against PROFILE.md and AGENT.md contracts."""
    result = ValidationResult()
    if not output_text or not output_text.strip():
        result.add_warning("EMPTY", "Output is empty")
        return result

    lower = output_text.lower()

    # No em dashes (PROFILE.md universal)
    em_dashes = EM_DASH_PATTERN.findall(output_text)
    if em_dashes:
        result.add_violation(
            "NO_EM_DASH",
            f"Found {len(em_dashes)} em/en dash(es). "
            "Use colons, semicolons, parentheses, or restructure."
        )

    # No filler (PROFILE.md anti-pattern)
    for phrase in FILLER_PHRASES:
        if phrase in lower:
            result.add_violation("NO_FILLER", f"Filler phrase: '{phrase}'")
            break

    # No unsolicited motivation (PROFILE.md anti-pattern)
    for phrase in MOTIVATION_PHRASES:
        if phrase in lower:
            result.add_violation("NO_MOTIVATION", f"Encouragement: '{phrase}'")
            break

    # Claim tags in structured output (skip chat)
    if active_mode != "chat":
        tier_num = int(task_tier[1]) if len(task_tier) == 2 and task_tier[0] == "T" else 3
        has_tags = any(tag in output_text for tag in ["[OBS]", "[DRV]", "[GEN]", "[SPEC]"])
        if tier_num >= 3 and not has_tags:
            result.add_warning(
                "CLAIM_TAGS",
                "No claim tags in T3+ structured output."
            )

    # Energy-appropriate length
    line_count = len(output_text.strip().split("\n"))
    if energy_level == "low" and line_count > 15:
        result.add_warning(
            "ENERGY_LOW",
            f"{line_count} lines in low-energy mode. Target: <=3 items."
        )
    if energy_level == "crash" and line_count > 5:
        result.add_violation(
            "ENERGY_CRASH",
            f"{line_count} lines in crash mode. Expected: state summary only."
        )

    # Verdict-first (PROFILE.md pattern compression)
    first_block = " ".join(output_text.strip().split("\n")[:3]).lower()
    for signal in ["before we begin", "first, let me explain", "to understand this", "let me start by"]:
        if signal in first_block:
            result.add_warning("VERDICT_FIRST", "Leads with context, not verdict.")
            break

    return result
