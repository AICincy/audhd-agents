"""Output validation against PROFILE.md cognitive contract.

Post-processing validation that checks model output for compliance
with hard constraints. Flags violations transparently rather than
silently fixing (per honesty protocol: explicit over implicit).

Resolves A-6: Output validation against cognitive contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of output validation against cognitive contract."""

    passed: bool = True
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_violation(self, rule: str, detail: str) -> None:
        """Add a hard violation (constraint breach)."""
        self.passed = False
        self.violations.append(f"[{rule}] {detail}")

    def add_warning(self, rule: str, detail: str) -> None:
        """Add a soft warning (best practice deviation)."""
        self.warnings.append(f"[{rule}] {detail}")


# Em dash variants: U+2014 (em dash), U+2013 (en dash), U+2012 (figure dash)
EM_DASH_PATTERN = re.compile(r"[\u2014\u2013\u2012]")

# PROFILE.md anti-pattern: filler phrases
FILLER_PHRASES = [
    "as an ai",
    "i'd be happy to",
    "great question",
    "that's a great",
    "let me help you",
    "absolutely!",
    "of course!",
    "sure thing",
    "no problem",
    "here's what i think",
    "have you tried",
    "have you considered",
    "i hope this helps",
    "feel free to",
]

# PROFILE.md anti-pattern: unsolicited motivation
MOTIVATION_PHRASES = [
    "you've got this",
    "keep going",
    "great job",
    "well done",
    "amazing work",
    "you're doing great",
    "stay positive",
    "believe in yourself",
    "proud of you",
    "keep it up",
]


def validate_output(
    output_text: str,
    active_mode: str = "execute",
    energy_level: str = "medium",
    task_tier: str = "T3",
) -> ValidationResult:
    """Validate model output against PROFILE.md and AGENT.md contracts.

    This is a post-processing check. It flags violations but does NOT
    modify the output (per honesty protocol: transparent, not opaque).
    Violations are logged and returned for the caller to handle.

    Args:
        output_text: Raw model output text.
        active_mode: Current PROFILE.md mode.
        energy_level: Current AGENT.md energy level.
        task_tier: Current AGENT.md task tier.

    Returns:
        ValidationResult with violations and warnings.
    """
    result = ValidationResult()

    if not output_text or not output_text.strip():
        result.add_warning("EMPTY", "Output is empty")
        return result

    lower = output_text.lower()

    # Rule: No em dashes (PROFILE.md universal constraint)
    em_dashes = EM_DASH_PATTERN.findall(output_text)
    if em_dashes:
        result.add_violation(
            "NO_EM_DASH",
            f"Found {len(em_dashes)} em/en dash(es). "
            "Use colons, semicolons, parentheses, or restructure."
        )

    # Rule: No filler phrases (PROFILE.md anti-pattern)
    for phrase in FILLER_PHRASES:
        if phrase in lower:
            result.add_violation(
                "NO_FILLER",
                f"Filler phrase detected: '{phrase}'"
            )
            break  # One violation is enough to flag

    # Rule: No unsolicited motivation (PROFILE.md anti-pattern)
    for phrase in MOTIVATION_PHRASES:
        if phrase in lower:
            result.add_violation(
                "NO_MOTIVATION",
                f"Unsolicited encouragement detected: '{phrase}'"
            )
            break

    # Rule: Claim tags in structured output (skip for chat mode)
    if active_mode != "chat":
        tier_num = int(task_tier[1]) if task_tier and len(task_tier) == 2 and task_tier[0] == "T" else 3
        has_tags = any(
            tag in output_text
            for tag in ["[OBS]", "[DRV]", "[GEN]", "[SPEC]"]
        )
        if tier_num >= 3 and not has_tags:
            result.add_warning(
                "CLAIM_TAGS",
                "No claim tags found in T3+ structured output. "
                "Consider adding [OBS], [DRV], [GEN], or [SPEC] tags."
            )

    # Rule: Energy-appropriate output length
    line_count = len(output_text.strip().split("\n"))
    if energy_level == "low" and line_count > 15:
        result.add_warning(
            "ENERGY_LOW",
            f"Output has {line_count} lines in low-energy mode. "
            "Target: 3 items or fewer, single next action."
        )

    if energy_level == "crash" and line_count > 5:
        result.add_violation(
            "ENERGY_CRASH",
            f"Output has {line_count} lines in crash mode. "
            "Expected: state summary + reassurance only."
        )

    # Rule: Verdict-first (PROFILE.md pattern compression)
    first_lines = output_text.strip().split("\n")[:3]
    first_block = " ".join(first_lines).lower()
    context_first_signals = [
        "before we begin",
        "first, let me explain",
        "to understand this",
        "let me start by",
        "to provide context",
    ]
    for signal in context_first_signals:
        if signal in first_block:
            result.add_warning(
                "VERDICT_FIRST",
                "Output appears to lead with context instead of verdict. "
                "Pattern compression: verdict first, supporting structure second."
            )
            break

    return result
