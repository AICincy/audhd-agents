"""Skill hooks (sk_hooks) runtime implementation. Resolves A-4.

Hook registry (17 hooks):
  Original 6:
    SK-DECOMP, SK-BRIDGE, SK-GATE, SK-VERIFY, SK-PRIORITIZE, SK-FORMAT
  New 11 (F2 fix):
    SK-REALITY, SK-ENERGY (always-on)
    SK-EXTERN, SK-RESUME, SK-MICRO, SK-ANCHOR
    SK-CODEREVIEW, SK-NUDGE, SK-A11Y, SK-SYS-AUDIT, SK-SYS-RECOVER
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from runtime.cognitive import CognitiveState


# Hooks that run on EVERY execution regardless of skill config
ALWAYS_ON_HOOKS: list[str] = ["SK-REALITY", "SK-ENERGY"]


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


# ---------------------------------------------------------------------------
# Original hooks (SK-DECOMP through SK-FORMAT)
# ---------------------------------------------------------------------------

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
            "- [ ] Output is ONLY state checkpoint",
            "- [ ] No analysis or deliverables",
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
    """SK-PRIORITIZE: Monotropism contract enforcement on high context switches."""
    result = HookResult()
    if ctx.cognitive_state.context_switches > 2:
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Monotropism Contract (SK-PRIORITIZE: active)\n"
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


# ---------------------------------------------------------------------------
# New hooks (F2 fix: SK-REALITY through SK-SYS-RECOVER)
# ---------------------------------------------------------------------------

def sk_reality(ctx: HookContext) -> HookResult:
    """SK-REALITY: Reality checker. Validates claims, flags drift/hallucination.

    Always-on hook. Injects reality-checking constraints into every prompt.
    RC-001: Cross-reference claims against provided evidence
    RC-002: Flag speculative content explicitly
    RC-003: Block untagged claims in T3+ output
    """
    result = HookResult()
    reality_block = (
        "\n\n## Reality Checker (SK-REALITY: always-on)\n"
        "Before finalizing output:\n"
        "- RC-001: Every factual claim must reference provided evidence or be tagged [SPEC]\n"
        "- RC-002: Speculative leaps must be flagged: 'This is inference, not confirmed'\n"
        "- RC-003: T3+ output with zero claim tags is non-compliant and must be revised\n"
        "- RC-004: If you cannot verify a claim, state so explicitly rather than asserting\n"
        "- RC-005: Check for phantom entities (names, URLs, versions that weren't in input)\n"
    )
    result.modified_prompt = (ctx.prompt or "") + reality_block
    return result


def sk_energy(ctx: HookContext) -> HookResult:
    """SK-ENERGY: Energy-adaptive routing enforcement.

    Always-on hook. Ensures output respects current energy level constraints.
    """
    result = HookResult()
    energy = ctx.cognitive_state.energy_level
    if energy == "low":
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Energy Routing (SK-ENERGY: low)\n"
            "- Maximum 3 items in output\n"
            "- Single micro-action as next step\n"
            "- No complex analysis or multi-part deliverables\n"
            "- Shortest viable response\n"
        )
    elif energy == "crash":
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Energy Routing (SK-ENERGY: CRASH)\n"
            "- OUTPUT ONLY: state checkpoint + single next action\n"
            "- NO inference. NO analysis. NO deliverables.\n"
            "- Save state and stop.\n"
        )
    # high/medium: no additional constraints
    return result


def sk_extern(ctx: HookContext) -> HookResult:
    """SK-EXTERN: External VoltAgent skill loading bridge.

    Detects references to external skills and injects loading instructions.
    """
    result = HookResult()
    if ctx.options.get("external_skill") or "voltagent:" in ctx.input_text.lower():
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## External Skill Bridge (SK-EXTERN)\n"
            "This execution uses an external VoltAgent skill definition.\n"
            "- Apply the skill's prompt_base.md as system context\n"
            "- Validate input against the skill's schema_base.json\n"
            "- Map model references to swarm aliases (G-PRO31, O-54, etc.)\n"
        )
    return result


def sk_resume(ctx: HookContext) -> HookResult:
    """SK-RESUME: 'Where Was I?' session resumption protocol."""
    result = HookResult()
    if ctx.cognitive_state.needs_resume():
        checkpoint = ctx.cognitive_state.resume_from or "unknown"
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Session Resume (SK-RESUME: checkpoint={checkpoint})\n"
            "Returning from interruption. Protocol:\n"
            "1. State what was in progress at checkpoint\n"
            "2. Summarize any partial results\n"
            "3. Present single next action to continue\n"
            "4. Do NOT restart from scratch\n"
        )
    return result


def sk_micro(ctx: HookContext) -> HookResult:
    """SK-MICRO: Micro-action decomposition for low-energy states."""
    result = HookResult()
    energy = ctx.cognitive_state.energy_level
    if energy == "low" and ctx.cognitive_state.task_tier_num >= 3:
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Micro-Action Mode (SK-MICRO: active)\n"
            "Task tier exceeds low-energy capacity. Decompose:\n"
            "- Extract the single smallest actionable step\n"
            "- Present ONLY that step\n"
            "- Queue remainder for when capacity recovers\n"
            "- State what is deferred and why\n"
        )
    return result


def sk_anchor(ctx: HookContext) -> HookResult:
    """SK-ANCHOR: Context anchoring for monotropism contract."""
    result = HookResult()
    if ctx.cognitive_state.active_thread:
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Context Anchor (SK-ANCHOR: thread={ctx.cognitive_state.active_thread})\n"
            "Monotropism contract active:\n"
            "- Stay on the declared thread objective\n"
            "- Do not introduce new topics without explicit announcement\n"
            "- If input implies a topic switch, announce it before executing\n"
        )
    return result


def sk_codereview(ctx: HookContext) -> HookResult:
    """SK-CODEREVIEW: Code review quality gate."""
    result = HookResult()
    if ctx.cognitive_state.active_mode in ("review", "rewrite") and ctx.options.get("code_review"):
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Code Review Gate (SK-CODEREVIEW)\n"
            "Review checklist:\n"
            "- [ ] No import drift (all imports resolve)\n"
            "- [ ] No phantom functions (all calls have definitions)\n"
            "- [ ] Schema consistency across files\n"
            "- [ ] Backward compatibility preserved or migration noted\n"
            "- [ ] Error handling covers new code paths\n"
            "- [ ] Tests updated or test plan provided\n"
        )
    return result


def sk_nudge(ctx: HookContext) -> HookResult:
    """SK-NUDGE: Refocus to declared objective when output drifts."""
    result = HookResult()
    if ctx.options.get("nudge_target"):
        target = ctx.options["nudge_target"]
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Refocus (SK-NUDGE: target={target})\n"
            "Previous output drifted from objective. Correct course:\n"
            f"- Primary objective: {target}\n"
            "- Discard tangential content\n"
            "- Produce targeted output only\n"
        )
    return result


def sk_a11y(ctx: HookContext) -> HookResult:
    """SK-A11Y: Accessibility compliance checker."""
    result = HookResult()
    if ctx.options.get("a11y_check") or ctx.cognitive_state.active_mode == "design":
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Accessibility Check (SK-A11Y)\n"
            "Verify output meets accessibility standards:\n"
            "- Alt text for any visual content\n"
            "- Semantic structure (headings, lists) over visual formatting\n"
            "- Color is never the sole differentiator\n"
            "- Plain language preferred over jargon\n"
            "- Screen reader compatibility considered\n"
        )
    return result


def sk_sys_audit(ctx: HookContext) -> HookResult:
    """SK-SYS-AUDIT: System-level audit trigger.

    Injects meta-layer reflex: audit the outcome-generating system,
    not just the surface output.
    """
    result = HookResult()
    if ctx.cognitive_state.task_tier_num >= 4:
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## System Audit (SK-SYS-AUDIT: T4+)\n"
            "Meta-layer reflex required:\n"
            "- What objective function is this system optimizing?\n"
            "- What constraints are active vs. assumed?\n"
            "- What incentives might distort the output?\n"
            "- What failure modes exist?\n"
            "- What measurement would validate correctness?\n"
        )
    return result


def sk_sys_recover(ctx: HookContext) -> HookResult:
    """SK-SYS-RECOVER: System recovery from failures.

    Activates when previous execution failed or produced non-compliant output.
    """
    result = HookResult()
    if ctx.options.get("recovery_from"):
        error_info = ctx.options["recovery_from"]
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Recovery Mode (SK-SYS-RECOVER)\n"
            f"Previous failure: {error_info}\n"
            "Recovery protocol:\n"
            "1. State the incorrect element and root cause\n"
            "2. Assess impact scope\n"
            "3. Produce corrected output\n"
            "4. Include revert path if correction fails\n"
        )
    return result


# ---------------------------------------------------------------------------
# Hook Registry
# ---------------------------------------------------------------------------

HOOK_REGISTRY: dict[str, Callable[[HookContext], HookResult]] = {
    "SK-DECOMP": sk_decomp,
    "SK-BRIDGE": sk_bridge,
    "SK-GATE": sk_gate,
    "SK-VERIFY": sk_verify,
    "SK-PRIORITIZE": sk_prioritize,
    "SK-FORMAT": sk_format,
    "SK-REALITY": sk_reality,
    "SK-ENERGY": sk_energy,
    "SK-EXTERN": sk_extern,
    "SK-RESUME": sk_resume,
    "SK-MICRO": sk_micro,
    "SK-ANCHOR": sk_anchor,
    "SK-CODEREVIEW": sk_codereview,
    "SK-NUDGE": sk_nudge,
    "SK-A11Y": sk_a11y,
    "SK-SYS-AUDIT": sk_sys_audit,
    "SK-SYS-RECOVER": sk_sys_recover,
}


def run_hooks(hook_names: list[str], ctx: HookContext) -> HookResult:
    """Execute hook chain in declared order, merging results.

    Always-on hooks (SK-REALITY, SK-ENERGY) run first regardless of
    whether they appear in hook_names.
    """
    # Prepend always-on hooks (deduplicate if already in list)
    effective_hooks = list(ALWAYS_ON_HOOKS)
    for name in hook_names:
        if name not in effective_hooks:
            effective_hooks.append(name)

    merged = HookResult()
    for name in effective_hooks:
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
