"""Skill hooks (sk_hooks) runtime implementation. Resolves A-4.

Hook registry (20 hooks):
  Original 6:
    SK-DECOMP, SK-BRIDGE, SK-GATE, SK-VERIFY, SK-PRIORITIZE, SK-FORMAT
  F2 additions (11):
    SK-REALITY, SK-ENERGY (always-on)
    SK-EXTERN, SK-RESUME, SK-MICRO, SK-ANCHOR
    SK-CODEREVIEW, SK-NUDGE, SK-A11Y, SK-SYS-AUDIT, SK-SYS-RECOVER
  Enhancement additions (3):
    SK-STT, SK-TTS, SK-TONE
"""

from __future__ import annotations

import json
import re
import time
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
    """SK-BRIDGE: Carry state between skill handoffs per AGENT.md format.

    Enhanced: Supports structured context objects (dict-based partial_results)
    in addition to string-based context parsing.
    """
    result = HookResult()
    bridged_parts: list[str] = []

    # Legacy string-based handoff detection
    if "HANDOFF" in ctx.input_text or "ARTIFACTS:" in ctx.input_text:
        context_match = re.search(
            r"CONTEXT:\s*(.+?)(?=\n\s*[A-Z_]+:|$)",
            ctx.input_text, re.DOTALL,
        )
        if context_match:
            bridged_parts.append(context_match.group(1).strip())

    # Structured context objects (dict or list)
    partial = ctx.options.get("partial_results")
    if partial:
        if isinstance(partial, dict):
            # Structured handoff: extract keyed context
            for key, value in partial.items():
                if isinstance(value, str):
                    bridged_parts.append(f"**{key}**: {value}")
                elif isinstance(value, list):
                    items = ", ".join(str(v) for v in value[:10])
                    bridged_parts.append(f"**{key}**: [{items}]")
                else:
                    bridged_parts.append(f"**{key}**: {value}")
        elif isinstance(partial, list):
            for item in partial[:10]:
                bridged_parts.append(f"- {item}")
        else:
            bridged_parts.append(str(partial))

    # Prior skill output bridging
    prior_output = ctx.options.get("prior_skill_output")
    if prior_output:
        if isinstance(prior_output, dict):
            summary = prior_output.get("summary", prior_output.get("output", str(prior_output)))
            bridged_parts.append(f"**Prior skill result**: {summary}")
        else:
            bridged_parts.append(f"**Prior skill result**: {prior_output}")

    if bridged_parts:
        result.bridged_context = "\n".join(bridged_parts)
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
# F2 hooks (SK-REALITY through SK-SYS-RECOVER)
# ---------------------------------------------------------------------------

def sk_reality(ctx: HookContext) -> HookResult:
    """SK-REALITY: Reality checker. Validates claims, flags drift/hallucination.

    Always-on hook.
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
    """SK-ENERGY: Energy-adaptive routing enforcement. Always-on hook."""
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
    return result


def sk_extern(ctx: HookContext) -> HookResult:
    """SK-EXTERN: External VoltAgent skill loading bridge."""
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
    """SK-ANCHOR: Context anchoring for monotropism contract.

    Enhanced: Maintains topic stack with recency tracking, attention decay
    calculation, and deferred topic queue.
    """
    result = HookResult()
    if not ctx.cognitive_state.active_thread:
        return result

    anchor_lines = [
        f"\n\n## Context Anchor (SK-ANCHOR: thread={ctx.cognitive_state.active_thread})",
        "Monotropism contract active:",
        "- Stay on the declared thread objective",
        "- Do not introduce new topics without explicit announcement",
        "- If input implies a topic switch, announce it before executing",
    ]

    # Topic stack from options (maintained by caller or prior hooks)
    topic_stack = ctx.options.get("topic_stack", [])
    if topic_stack:
        anchor_lines.append("")
        anchor_lines.append("### Topic Stack (most recent first)")
        for i, topic in enumerate(reversed(topic_stack[-5:])):
            recency = topic.get("recency", 1.0) if isinstance(topic, dict) else 1.0
            name = topic.get("name", str(topic)) if isinstance(topic, dict) else str(topic)
            decay = max(0.0, recency - (i * 0.15))
            anchor_lines.append(f"- {name} (attention: {decay:.0%})")

    # Deferred topics queue
    deferred = ctx.options.get("deferred_topics", [])
    if deferred:
        anchor_lines.append("")
        anchor_lines.append("### Deferred (parked, not forgotten)")
        for topic in deferred[:5]:
            anchor_lines.append(f"- {topic}")

    # Context switch cost warning
    switches = ctx.cognitive_state.context_switches
    if switches > 0:
        cost = "low" if switches <= 1 else "medium" if switches <= 3 else "high"
        anchor_lines.append(f"")
        anchor_lines.append(f"Switch cost: {cost} ({switches} switches this session)")

    result.modified_prompt = (ctx.prompt or "") + "\n".join(anchor_lines)
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
    """SK-SYS-AUDIT: System-level audit trigger for T4+."""
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
    """SK-SYS-RECOVER: System recovery from failures."""
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
# Enhancement hooks (SK-STT, SK-TTS, SK-TONE)
# ---------------------------------------------------------------------------

# SK-STT filler words to strip (preserves semantic fillers)
_STT_FILLERS = {
    "um", "uh", "like", "you know", "i mean", "basically",
    "literally", "right", "so", "actually", "honestly",
}

# SK-STT topic shift signal words
_STT_SHIFT_SIGNALS = [
    "oh wait", "actually", "oh and also", "sidebar", "tangent",
    "oh one more thing", "before i forget", "unrelated but",
    "switching gears", "different topic",
]


def sk_stt(ctx: HookContext) -> HookResult:
    """SK-STT: Speech-to-text preprocessing for AuDHD speech patterns.

    Pre-execute hook. Normalizes raw transcription:
    - Removes false starts and restart loops
    - Strips filler words (preserving semantic ones)
    - Detects topic shifts and queues deferred topics
    - Extracts compressed multi-intent bursts
    """
    result = HookResult()
    raw = ctx.options.get("stt_raw_transcript")
    if not raw:
        return result

    energy = ctx.cognitive_state.energy_level
    text = raw.strip()

    # Crash mode: pass through unchanged
    if energy == "crash":
        result.modified_input = text
        return result

    cleaned = text
    stt_flags: list[str] = []
    deferred_topics: list[str] = []

    # 1. False start removal: collapse "I need to... wait, " patterns
    restart_pattern = re.compile(
        r"(?:I\s+(?:need|want|was|should|think)\s+to\s+)?"
        r"(?:\.{2,}|,)?\s*(?:wait|no|actually|sorry|let me restart)"
        r"[,.]?\s*",
        re.IGNORECASE,
    )
    if restart_pattern.search(cleaned):
        stt_flags.append("STT-RESTART")
        cleaned = restart_pattern.sub("", cleaned).strip()

    # 2. Filler removal (sentence-initial 'so', non-comparative 'like')
    words = cleaned.split()
    filtered_words = []
    for i, word in enumerate(words):
        lower = word.lower().strip(".,!?")
        if lower in _STT_FILLERS:
            # Keep 'i mean' when it precedes a correction
            if lower == "i" and i + 1 < len(words) and words[i + 1].lower() == "mean":
                filtered_words.append(word)
            continue
        filtered_words.append(word)
    if len(filtered_words) < len(words) * 0.7:
        stt_flags.append("STT-FILLER-HEAVY")
    cleaned = " ".join(filtered_words)

    # 3. Topic shift detection
    for signal in _STT_SHIFT_SIGNALS:
        if signal in cleaned.lower():
            parts = re.split(re.escape(signal), cleaned, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2 and parts[1].strip():
                deferred_topics.append(parts[1].strip())
                cleaned = parts[0].strip()
                break

    # 4. Compressed burst detection (low energy: extract only first intent)
    if " and " in cleaned or " also " in cleaned:
        intent_pattern = re.compile(
            r"\b(?:and\s+(?:then\s+)?(?:also\s+)?|also\s+)"
            r"(?:can\s+you\s+|please\s+|could\s+you\s+)?",
            re.IGNORECASE,
        )
        intents = intent_pattern.split(cleaned)
        intents = [i.strip() for i in intents if i.strip()]
        if len(intents) > 1:
            stt_flags.append("STT-MULTI-INTENT")
            if energy == "low":
                deferred_topics.extend(intents[1:])
                cleaned = intents[0]

    # Store results
    result.modified_input = cleaned
    if deferred_topics:
        if result.modified_options is None:
            result.modified_options = {}
        result.modified_options["deferred_topics"] = deferred_topics
    if stt_flags:
        if result.modified_options is None:
            result.modified_options = {}
        result.modified_options["stt_flags"] = stt_flags

    return result


# SK-TTS voice parameter presets by energy level
_TTS_VOICE_PARAMS: dict[str, dict[str, float]] = {
    "high": {"rate": 1.0, "volume": 0.8, "pause_multiplier": 1.0},
    "medium": {"rate": 0.95, "volume": 0.8, "pause_multiplier": 1.1},
    "low": {"rate": 0.85, "volume": 0.7, "pause_multiplier": 1.25},
    "crash": {"rate": 0.75, "volume": 0.6, "pause_multiplier": 1.5},
}

# SK-TTS max output items by energy
_TTS_MAX_ITEMS: dict[str, int] = {
    "high": 999,
    "medium": 10,
    "low": 3,
    "crash": 1,
}


def sk_tts(ctx: HookContext) -> HookResult:
    """SK-TTS: Text-to-speech output routing.

    Post-execute style hook (runs as prompt injection to shape output
    for speech consumption). Injects voice parameters and structure
    flattening directives.
    """
    result = HookResult()
    if not ctx.options.get("tts_enabled"):
        return result

    energy = ctx.cognitive_state.energy_level
    e_key = energy.value if hasattr(energy, "value") else str(energy)
    params = _TTS_VOICE_PARAMS.get(e_key, _TTS_VOICE_PARAMS["medium"])
    max_items = _TTS_MAX_ITEMS.get(e_key, 10)

    tts_block = (
        f"\n\n## Speech Output Mode (SK-TTS: {e_key})\n"
        "Output will be consumed as audio. Adapt:\n"
        "- Flatten tables to sequential comparisons\n"
        "- Flatten nested lists to numbered items with depth cues\n"
        "- Replace headers with natural transitions ('Moving to...')\n"
        "- Split compound sentences at conjunctions\n"
        "- Expand abbreviations and acronyms on first use\n"
        f"- Maximum {max_items} items in any list\n"
        "- Claim tags spoken: [OBS]='Observed:', [DRV]='Inferred:', [SPEC]='Unverified:'\n"
    )

    if e_key == "crash":
        tts_block += "- Single sentence only. No structure.\n"
    elif e_key == "low":
        tts_block += "- Maximum 3 sentences. Shortest viable.\n"

    # Store voice params for downstream TTS engine
    if result.modified_options is None:
        result.modified_options = {}
    result.modified_options["tts_voice_params"] = params

    result.modified_prompt = (ctx.prompt or "") + tts_block
    return result


# SK-TONE register definitions
_TONE_MATRIX: dict[str, dict[str, str]] = {
    "execute": {"register": "technical_direct", "density": "maximum", "formality": "low", "personality": "minimal"},
    "draft": {"register": "audience_matched", "density": "varies", "formality": "matched", "personality": "calibrated"},
    "rewrite": {"register": "source_matched", "density": "preserve", "formality": "preserve", "personality": "minimal"},
    "review": {"register": "analytical", "density": "high", "formality": "medium", "personality": "minimal"},
    "decide": {"register": "neutral_balanced", "density": "high", "formality": "medium", "personality": "minimal"},
    "troubleshoot": {"register": "terse_action", "density": "maximum", "formality": "low", "personality": "zero"},
    "design": {"register": "architectural", "density": "high", "formality": "medium", "personality": "minimal"},
    "summarize": {"register": "dense_verdict", "density": "maximum", "formality": "low", "personality": "minimal"},
    "osint": {"register": "clinical_tagged", "density": "maximum", "formality": "high", "personality": "zero"},
    "chat": {"register": "conversational", "density": "medium", "formality": "low", "personality": "present"},
}

_TONE_AUDIENCE: dict[str, str] = {
    "technical": "Jargon allowed. Assume domain fluency. No hand-holding.",
    "executive": "Lead with impact. Minimize implementation detail. Business outcomes first.",
    "client": "Professional. No internal references. Action-oriented.",
    "peer": "Direct. Skip shared context. No social scaffolding.",
    "public": "Accessible language. Define terms. No assumptions.",
    "self": "Maximum compression. Shorthand OK. No social scaffolding.",
}

_TONE_BLOCKED = [
    "synergy", "leverage", "circle back", "touch base", "deep dive",
    "move the needle", "low-hanging fruit", "bandwidth",
    "i think maybe", "it might be possible that",
    "i'm not sure but", "hope this helps",
]


def sk_tone(ctx: HookContext) -> HookResult:
    """SK-TONE: Tone and register adaptation by mode and audience.

    Zero-cost prompt injection. No additional model inference.
    Automatically selects register from mode, overridable via options.
    """
    result = HookResult()
    mode = ctx.cognitive_state.active_mode
    energy = ctx.cognitive_state.energy_level
    e_key = energy.value if hasattr(energy, "value") else str(energy)

    # Crash mode: no tone processing
    if e_key == "crash":
        return result

    tone = _TONE_MATRIX.get(mode, _TONE_MATRIX["execute"])
    audience = ctx.options.get("audience", "self")
    audience_directive = _TONE_AUDIENCE.get(audience, _TONE_AUDIENCE["self"])

    # Formality override
    formality = ctx.options.get("formality_override") or tone["formality"]

    tone_lines = [
        f"\n\n## Tone Directive (SK-TONE: {tone['register']}, audience={audience})",
        f"Register: {tone['register']}. Density: {tone['density']}. Formality: {formality}.",
        f"Audience: {audience_directive}",
    ]

    # Energy-specific tone adjustments
    if e_key == "low":
        tone_lines.append("Energy-low override: bare minimum. No social scaffolding. Direct answers only.")
    elif e_key == "medium":
        tone_lines.append("Standard register. No small talk.")

    # Blocked patterns
    tone_lines.append("")
    tone_lines.append("Blocked: " + ", ".join(f"'{p}'" for p in _TONE_BLOCKED[:6]) + ", and similar.")

    result.modified_prompt = (ctx.prompt or "") + "\n".join(tone_lines)
    return result


# ---------------------------------------------------------------------------
# Hook Registry
# ---------------------------------------------------------------------------

HOOK_REGISTRY: dict[str, Callable[[HookContext], HookResult]] = {
    # Original 6
    "SK-DECOMP": sk_decomp,
    "SK-BRIDGE": sk_bridge,
    "SK-GATE": sk_gate,
    "SK-VERIFY": sk_verify,
    "SK-PRIORITIZE": sk_prioritize,
    "SK-FORMAT": sk_format,
    # F2 additions
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
    # Enhancements
    "SK-STT": sk_stt,
    "SK-TTS": sk_tts,
    "SK-TONE": sk_tone,
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
