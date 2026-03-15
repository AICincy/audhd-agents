"""Skill hooks (sk_hooks) runtime implementation. Resolves A-4.

Hook registry:
- SK-DECOMP: Decompose complex input into independent sub-tasks
- SK-BRIDGE: Bridge context between skill handoffs
- SK-GATE: Quality gate via prompt injection
- SK-VERIFY: Claim verification requirements by tier
- SK-PRIORITIZE: Monotropism-aware prioritization
- SK-FORMAT: Mode-aware output template enforcement
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
    """SK-DECOMP: Decompose T4+ input into parallel sub-tasks."""
    result = HookResult()
    if ctx.cognitive_state.task_tier_num < 4:
        return result
    lines = ctx.input_text.strip().split("\n")
    task_lines = [
        line.strip() for line in lines
        if line.strip() and (
            line.strip().startswith(("-", "*", "1.", "2.", "3.", "4.", "5."))
            or ": " in line
        )
    ]
    if len(task_lines) > 1:
        result.decomposed_tasks = task_lines
        task_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(task_lines))
        result.modified_prompt = (
            ctx.prompt
            + f"\n\n## Decomposed Sub-tasks (SK-DECOMP: {len(task_lines)} found)\n"
            + task_list
            + "\n\nProcess independently where possible. Merge into single deliverable."
        )
    return result


def sk_bridge(ctx: HookContext) -> HookResult:
    """SK-BRIDGE: Carry state between skill handoffs per AGENT.md format."""
    result = HookResult()
    if "HANDOFF" in ctx.input_text or "ARTIFACTS:" in ctx.input_text:
        context_match = re.search(
            r"CONTEXT:\s*(.+?)(?=\n\s*[A-Z_]+:|$)",
            ctx.input_text, re.DOTALL,
        )
        if context_match:
            result.bridged_context = context_match.group(1).strip()
    partial = ctx.options.get("partial_results")
    if partial:
        bridge_text = str(partial)
        result.bridged_context += ("\n" if result.bridged_context else "") + bridge_text
        result.modified_prompt = (
            ctx.prompt + f"\n\n## Bridged Context (SK-BRIDGE)\n{result.bridged_context}"
        )
    return result


def sk_gate(ctx: HookContext) -> HookResult:
    """SK-GATE: Inject PROFILE.md constraint checklist into prompt."""
    result = HookResult()
    gate_lines = [
        "\n\n## Quality Gate (SK-GATE: enforced at runtime)",
        "Before producing final output, verify:",
    ]
    energy = ctx.cognitive_state.energy_level
    if energy == "low":
        gate_lines.extend([
            "- [ ] Output is 3 items or fewer (low energy mode)",
            "- [ ] Single next action as smallest possible step",
        ])
    elif energy == "crash":
        gate_lines.extend([
            "- [ ] Output is ONLY state summary + reassurance",
            "- [ ] No new analysis or deliverables",
        ])
    gate_lines.extend([
        "- [ ] No em dashes anywhere in output",
        "- [ ] No padding, filler, or decorative prose",
        "- [ ] No unsolicited encouragement or motivation",
        "- [ ] Verdict/synthesis before supporting detail",
        "- [ ] Tables for any comparison or decision content",
    ])
    if ctx.cognitive_state.active_mode != "chat":
        gate_lines.append(
            "- [ ] Claim tags on factual claims ([OBS], [DRV], [GEN], [SPEC])"
        )
    if ctx.cognitive_state.task_tier_num >= 5:
        gate_lines.append(
            "- [ ] MANDATORY: Flag for dual-model verification before delivery"
        )
    result.modified_prompt = ctx.prompt + "\n".join(gate_lines)
    return result


def sk_verify(ctx: HookContext) -> HookResult:
    """SK-VERIFY: Inject verification requirements by AGENT.md tier."""
    result = HookResult()
    tier = ctx.cognitive_state.task_tier_num
    if tier < 3:
        return result
    levels = {3: "optional", 4: "recommended", 5: "mandatory_dual_model"}
    level = levels.get(tier, "optional")
    verify_block = (
        f"\n\n## Verification Requirements (SK-VERIFY: {level})\n"
        "- Tag every factual claim with [OBS], [DRV], [GEN], or [SPEC]\n"
        "- For [OBS] claims: cite the source\n"
        "- For [SPEC] claims: state what would verify or falsify\n"
    )
    if level == "mandatory_dual_model":
        verify_block += (
            "- MANDATORY: Include confidence score per major claim\n"
            "- MANDATORY: Flag for second-model review before delivery\n"
        )
    elif level == "recommended":
        verify_block += "- RECOMMENDED: Include confidence assessment for key claims\n"
    result.modified_prompt = (ctx.prompt or "") + verify_block
    return result


def sk_prioritize(ctx: HookContext) -> HookResult:
    """SK-PRIORITIZE: Monotropism guard when context switches exceed threshold."""
    result = HookResult()
    if ctx.cognitive_state.context_switches > 2:
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Monotropism Guard (SK-PRIORITIZE: active)\n"
            "Multiple context switches detected. Enforce:\n"
            "- Present exactly ONE result at a time\n"
            "- Do not scatter across tangents\n"
            "- If multiple items: rank by leverage, present #1 only, "
            "queue rest for next action\n"
            "- Announce any topic shift before executing it\n"
        )
    return result


def sk_format(ctx: HookContext) -> HookResult:
    """SK-FORMAT: Inject PROFILE.md output template for active mode."""
    result = HookResult()
    mode = ctx.cognitive_state.active_mode
    templates = {
        "execute": "Goal, Constraints, Model, Output, Pressure test, Next actions",
        "decide": "Option | Upside | Downside | Cost to try | Time to try | Revert path | Risks | Notes",
        "troubleshoot": "Hypothesis | Evidence for | Evidence against | One test | Expected result | Fix if confirmed | Revert if wrong",
        "review": "Finding | Severity | Evidence | Recommendation",
        "summarize": "Verdict first. Key points as bullets. No skeleton.",
        "chat": "No skeleton. High density per sentence. Follow operator branch.",
        "draft": "Produce the artifact directly. No meta-commentary.",
        "rewrite": "Produce the revised artifact directly. No meta-commentary.",
        "design": "Architecture | Invariants | Interfaces | State transitions | Failure modes",
        "osint": "Target summary | Entity map | Relationship graph | Conflicts | Confidence | Next targets",
    }
    template = templates.get(mode)
    if template and mode != "chat":
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Output Template (SK-FORMAT: {mode} mode)\n"
            f"Structure output as: {template}\n"
        )
    return result


HOOK_REGISTRY: dict[str, Callable[[HookContext], HookResult]] = {
    "SK-DECOMP": sk_decomp,
    "SK-BRIDGE": sk_bridge,
    "SK-GATE": sk_gate,
    "SK-VERIFY": sk_verify,
    "SK-PRIORITIZE": sk_prioritize,
    "SK-FORMAT": sk_format,
}


def run_hooks(hook_names: list[str], ctx: HookContext) -> HookResult:
    """Execute hook chain in declared order, merging results."""
    merged = HookResult()
    for name in hook_names:
        hook_fn = HOOK_REGISTRY.get(name)
        if not hook_fn:
            merged.validation_warnings.append(f"Unknown hook: {name}")
            continue
        result = hook_fn(ctx)
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
