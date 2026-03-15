"""Skill hooks (sk_hooks) runtime implementation.

Converts phantom hook declarations in skill.yaml into callable
pre-processing and post-processing functions. Resolves A-4.

Hook registry from AGENT.md and skill.yaml conventions:
- SK-DECOMP: Decompose complex input into independent sub-tasks
- SK-BRIDGE: Bridge context between skill handoffs (carry state)
- SK-GATE: Gate output quality before returning (validation checkpoint)
- SK-VERIFY: Cross-reference claims against available evidence
- SK-PRIORITIZE: Apply monotropism-aware task prioritization
- SK-FORMAT: Enforce PROFILE.md output constraints

Hooks run in declared order. Pre-hooks modify input/prompt before
model execution. Post-hooks inject validation instructions into
the prompt so the model self-checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from runtime.cognitive import CognitiveState


@dataclass
class HookContext:
    """Context passed to hook functions."""

    skill_id: str
    cognitive_state: CognitiveState
    input_text: str
    prompt: str
    options: dict[str, Any]


@dataclass
class HookResult:
    """Result from a hook execution."""

    modified_input: str | None = None
    modified_prompt: str | None = None
    modified_options: dict[str, Any] | None = None
    gate_passed: bool = True
    gate_reason: str = ""
    decomposed_tasks: list[str] | None = None
    bridged_context: str = ""
    validation_warnings: list[str] = field(default_factory=list)


def sk_decomp(ctx: HookContext) -> HookResult:
    """SK-DECOMP: Decompose complex input into parallel sub-tasks.

    Triggered for T4+ tasks. Identifies independent workstreams
    that can be processed concurrently per AGENT.md topology.
    For T1-T3: pass-through (no decomposition overhead).
    """
    result = HookResult()

    # Only decompose complex tasks
    if ctx.cognitive_state.task_tier_num < 4:
        return result

    # Identify list-like structures suggesting multiple independent items
    lines = ctx.input_text.strip().split("\n")
    task_lines = [
        line.strip()
        for line in lines
        if line.strip() and (
            line.strip().startswith(("-", "*", "1.", "2.", "3.", "4.", "5."))
            or ": " in line
        )
    ]

    if len(task_lines) > 1:
        result.decomposed_tasks = task_lines
        # Add decomposition hint to prompt
        task_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(task_lines))
        result.modified_prompt = (
            ctx.prompt
            + f"\n\n## Decomposed Sub-tasks (SK-DECOMP: {len(task_lines)} identified)\n"
            + task_list
            + "\n\nProcess independently where possible. Merge into single deliverable."
        )

    return result


def sk_bridge(ctx: HookContext) -> HookResult:
    """SK-BRIDGE: Carry state between skill handoffs.

    Implements AGENT.md handoff format: extracts CONTEXT, ARTIFACTS,
    CONSTRAINTS from prior results and injects into current input.
    """
    result = HookResult()

    # Check for AGENT.md handoff markers in input
    if "HANDOFF" in ctx.input_text or "ARTIFACTS:" in ctx.input_text:
        context_match = re.search(
            r"CONTEXT:\s*(.+?)(?=\n\s*[A-Z_]+:|$)",
            ctx.input_text,
            re.DOTALL,
        )
        if context_match:
            result.bridged_context = context_match.group(1).strip()

    # Check for partial results in options (inter-skill state)
    partial = ctx.options.get("partial_results")
    if partial:
        bridge_text = str(partial)
        result.bridged_context += ("\n" if result.bridged_context else "") + bridge_text
        result.modified_prompt = (
            ctx.prompt
            + f"\n\n## Bridged Context (SK-BRIDGE)\n{result.bridged_context}"
        )

    return result


def sk_gate(ctx: HookContext) -> HookResult:
    """SK-GATE: Quality gate via prompt injection.

    Injects PROFILE.md constraint checklist into the prompt so the
    model self-validates before producing final output. This is a
    pre-execution gate (prompt-level), not post-execution.
    """
    result = HookResult()

    gate_lines = [
        "\n\n## Quality Gate (SK-GATE: enforced at runtime)",
        "Before producing final output, verify each constraint:",
    ]

    # Energy-appropriate output check
    energy = ctx.cognitive_state.energy_level
    if energy == "low":
        gate_lines.extend([
            "- [ ] Output is 3 items or fewer (low energy mode)",
            "- [ ] Single next action provided as smallest possible step",
        ])
    elif energy == "crash":
        gate_lines.extend([
            "- [ ] Output is ONLY state summary + reassurance",
            "- [ ] No new analysis or deliverables",
        ])

    # Universal PROFILE.md checks
    gate_lines.extend([
        "- [ ] No em dashes anywhere in output",
        "- [ ] No padding, filler, or decorative prose",
        "- [ ] No unsolicited encouragement or motivation",
        "- [ ] Verdict/synthesis appears before supporting detail",
        "- [ ] Tables used for any comparison or decision content",
    ])

    # Claim tag check for structured output
    if ctx.cognitive_state.active_mode != "chat":
        gate_lines.append(
            "- [ ] Claim tags present on factual claims ([OBS], [DRV], [GEN], [SPEC])"
        )

    # T5 verification requirement from AGENT.md
    if ctx.cognitive_state.task_tier_num >= 5:
        gate_lines.append(
            "- [ ] MANDATORY: Flag output for dual-model verification before delivery"
        )

    result.modified_prompt = ctx.prompt + "\n".join(gate_lines)
    return result


def sk_verify(ctx: HookContext) -> HookResult:
    """SK-VERIFY: Inject verification requirements based on task tier.

    From AGENT.md Task Classification:
    - T1-T2: No verification
    - T3: Optional verification
    - T4: Recommended verification
    - T5: Mandatory dual-model verification
    """
    result = HookResult()

    tier = ctx.cognitive_state.task_tier_num
    if tier < 3:
        return result

    levels = {3: "optional", 4: "recommended", 5: "mandatory_dual_model"}
    level = levels.get(tier, "optional")

    verify_block = (
        f"\n\n## Verification Requirements (SK-VERIFY: {level})\n"
        f"- Tag every factual claim with [OBS], [DRV], [GEN], or [SPEC]\n"
        f"- For [OBS] claims: cite the source\n"
        f"- For [SPEC] claims: state what would verify or falsify\n"
    )
    if level == "mandatory_dual_model":
        verify_block += (
            "- MANDATORY: Include confidence score per major claim\n"
            "- MANDATORY: Flag for second-model review before delivery\n"
        )
    elif level == "recommended":
        verify_block += (
            "- RECOMMENDED: Include confidence assessment for key claims\n"
        )

    result.modified_prompt = (ctx.prompt or "") + verify_block
    return result


def sk_prioritize(ctx: HookContext) -> HookResult:
    """SK-PRIORITIZE: Monotropism-aware prioritization.

    When context switches exceed threshold, enforce single-thread
    focus per PROFILE.md monotropism contract.
    """
    result = HookResult()

    if ctx.cognitive_state.context_switches > 2:
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Monotropism Guard (SK-PRIORITIZE: active)\n"
            "Multiple context switches detected. Enforce:\n"
            "- Present exactly ONE result at a time\n"
            "- Do not scatter across tangents\n"
            "- If multiple items: rank by leverage, present #1 only, "
            "queue rest as numbered list for next action\n"
            "- Announce any topic shift before executing it\n"
        )

    return result


def sk_format(ctx: HookContext) -> HookResult:
    """SK-FORMAT: Mode-aware output template enforcement.

    Injects the correct PROFILE.md output template based on
    the active mode from cognitive state.
    """
    result = HookResult()

    mode = ctx.cognitive_state.active_mode
    templates = {
        "execute": "Goal, Constraints, Model, Output, Pressure test, Next actions",
        "decide": "Option | Upside | Downside | Cost to try | Time to try | Revert path | Risks | Notes",
        "troubleshoot": "Hypothesis | Evidence for | Evidence against | One test | Expected result | Fix if confirmed | Revert if wrong",
        "review": "Finding | Severity | Evidence | Recommendation",
        "summarize": "Verdict first. Key points as bullets. No skeleton.",
        "chat": "No skeleton. High density per sentence. Follow the branch operator opens.",
        "draft": "Produce the artifact directly. No meta-commentary.",
        "rewrite": "Produce the revised artifact directly. No meta-commentary.",
        "design": "Architecture | Invariants | Interfaces | State transitions | Failure modes",
        "osint": "Target summary | Entity map | Relationship graph | Conflicts | Confidence | Next targets",
    }

    template = templates.get(mode)
    if template and mode != "chat":
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Output Template (SK-FORMAT: {mode} mode)\n"
            f"Structure your output as: {template}\n"
        )

    return result


# Hook registry: maps hook names from skill.yaml to implementations
HOOK_REGISTRY: dict[str, Callable[[HookContext], HookResult]] = {
    "SK-DECOMP": sk_decomp,
    "SK-BRIDGE": sk_bridge,
    "SK-GATE": sk_gate,
    "SK-VERIFY": sk_verify,
    "SK-PRIORITIZE": sk_prioritize,
    "SK-FORMAT": sk_format,
}


def run_hooks(
    hook_names: list[str],
    ctx: HookContext,
) -> HookResult:
    """Execute a chain of hooks in declared order, merging results.

    Each hook receives the (potentially modified) context from prior hooks.
    Results are merged: later hooks can override earlier modifications.

    Args:
        hook_names: List of hook names from skill.yaml sk_hooks field.
        ctx: Mutable hook context (modified in-place by hooks).

    Returns:
        Merged HookResult with all modifications and warnings.
    """
    merged = HookResult()

    for name in hook_names:
        hook_fn = HOOK_REGISTRY.get(name)
        if not hook_fn:
            merged.validation_warnings.append(f"Unknown hook: {name}")
            continue

        result = hook_fn(ctx)

        # Merge: later hooks override earlier ones
        if result.modified_input:
            merged.modified_input = result.modified_input
            ctx.input_text = result.modified_input

        if result.modified_prompt:
            merged.modified_prompt = result.modified_prompt
            ctx.prompt = result.modified_prompt

        if result.modified_options:
            if merged.modified_options is None:
                merged.modified_options = {}
            merged.modified_options.update(result.modified_options)

        if not result.gate_passed:
            merged.gate_passed = False
            merged.gate_reason = result.gate_reason

        if result.decomposed_tasks:
            merged.decomposed_tasks = result.decomposed_tasks

        if result.bridged_context:
            sep = "\n" if merged.bridged_context else ""
            merged.bridged_context += sep + result.bridged_context

        if result.validation_warnings:
            merged.validation_warnings.extend(result.validation_warnings)

    return merged
