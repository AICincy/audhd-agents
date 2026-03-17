"""Skill hooks (sk_hooks) runtime implementation. Resolves A-4.

Hook registry (20 hooks):
  Original 6:
    decompose, bridge, quality-gate, verify, focus, format
  F2 additions (11):
    reality-check, energy-route (always-on)
    load-skill, resume, micro-step, anchor
    code-review, refocus, accessibility, system-audit, recover
  Enhancement additions (3):
    speech-input, speech-output, tone
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from runtime.cognitive import CognitiveState


# Hooks that run on EVERY execution regardless of skill config
ALWAYS_ON_HOOKS: list[str] = ["reality-check", "energy-route"]


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
# Original hooks (decompose through format)
# ---------------------------------------------------------------------------

def sk_decomp(ctx: HookContext) -> HookResult:
    """decompose: Decompose T4+ input into parallel sub-tasks."""
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
            + f"\n\n## Decomposed Sub-tasks (decompose: {len(task_lines)} found)\n"
            + task_list
            + "\nProcess independently where possible. Merge into single deliverable."
        )
    return result


def sk_bridge(ctx: HookContext) -> HookResult:
    """bridge: Carry state between skill handoffs per AGENT.md format.

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
            ctx.prompt + f"\n\n## Bridged Context (bridge)\n{result.bridged_context}"
        )

    return result


def sk_gate(ctx: HookContext) -> HookResult:
    """quality-gate: Inject PROFILE.md constraint checklist into prompt."""
    result = HookResult()
    gate_lines = [
        "\n\n## Quality Gate (quality-gate: enforced at runtime)",
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
            "- [ ] Claim tags on factual claims ([observed], [inferred], [general], [unverified])"
        )
    if ctx.cognitive_state.task_tier_num >= 5:
        gate_lines.append(
            "- [ ] MANDATORY: Flag for dual-model verification before delivery"
        )
    result.modified_prompt = ctx.prompt + "\n".join(gate_lines)
    return result


def sk_verify(ctx: HookContext) -> HookResult:
    """verify: Inject verification requirements by AGENT.md tier."""
    result = HookResult()
    tier = ctx.cognitive_state.task_tier_num
    if tier < 3:
        return result
    levels = {3: "optional", 4: "recommended", 5: "mandatory_dual_model"}
    level = levels.get(tier, "optional")
    verify_block = (
        f"\n\n## Verification Requirements (verify: {level})\n"
        "- Tag every factual claim with [observed], [inferred], [general], or [unverified]\n"
        "- For [observed] claims: cite the source\n"
        "- For [unverified] claims: state what would verify or falsify\n"
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
    """focus: Monotropism contract enforcement on high context switches."""
    result = HookResult()
    if ctx.cognitive_state.context_switches > 2:
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Monotropism Contract (focus: active)\n"
            "Multiple context switches detected. Enforce:\n"
            "- Present exactly ONE result at a time\n"
            "- Do not scatter across tangents\n"
            "- If multiple items: rank by leverage, present #1 only, "
            "queue rest for next action\n"
            "- Announce any topic shift before executing it\n"
        )
    return result


def sk_format(ctx: HookContext) -> HookResult:
    """format: Inject PROFILE.md output template for active mode."""
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
            f"\n\n## Output Template (format: {mode} mode)\n"
            f"Structure output as: {template}\n"
        )
    return result


# ---------------------------------------------------------------------------
# F2 hooks (reality-check through recover)
# ---------------------------------------------------------------------------

def sk_reality(ctx: HookContext) -> HookResult:
    """reality-check: Reality checker. Validates claims, flags drift/hallucination.

    Always-on hook.
    RC-001: Cross-reference claims against provided evidence
    RC-002: Flag speculative content explicitly
    RC-003: Block untagged claims in T3+ output
    """
    result = HookResult()
    reality_block = (
        "\n\n## Reality Checker (reality-check: always-on)\n"
        "Before finalizing output:\n"
        "- RC-001: Every factual claim must reference provided evidence or be tagged [unverified]\n"
        "- RC-002: Speculative leaps must be flagged: 'This is inference, not confirmed'\n"
        "- RC-003: T3+ output with zero claim tags is non-compliant and must be revised\n"
        "- RC-004: If you cannot verify a claim, state so explicitly rather than asserting\n"
        "- RC-005: Check for phantom entities (names, URLs, versions that weren't in input)\n"
    )
    result.modified_prompt = (ctx.prompt or "") + reality_block
    return result


def sk_energy(ctx: HookContext) -> HookResult:
    """energy-route: Energy-adaptive routing enforcement. Always-on hook."""
    result = HookResult()
    energy = ctx.cognitive_state.energy_level
    if energy == "low":
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Energy Routing (energy-route: low)\n"
            "- Maximum 3 items in output\n"
            "- Single micro-action as next step\n"
            "- No complex analysis or multi-part deliverables\n"
            "- Shortest viable response\n"
        )
    elif energy == "crash":
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Energy Routing (energy-route: CRASH)\n"
            "- OUTPUT ONLY: state checkpoint + single next action\n"
            "- NO inference. NO analysis. NO deliverables.\n"
            "- Save state and stop.\n"
        )
    return result


def sk_extern(ctx: HookContext) -> HookResult:
    """load-skill: External VoltAgent skill loading bridge."""
    result = HookResult()
    if ctx.options.get("external_skill") or "voltagent:" in ctx.input_text.lower():
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## External Skill Bridge (load-skill)\n"
            "This execution uses an external VoltAgent skill definition.\n"
            "- Apply the skill's prompt_base.md as system context\n"
            "- Validate input against the skill's schema_base.json\n"
            "- Map model references to provider names (gemini-2.5-pro, o1, etc.)\n"
        )
    return result


def sk_resume(ctx: HookContext) -> HookResult:
    """resume: 'Where Was I?' session resumption protocol."""
    result = HookResult()
    if ctx.cognitive_state.needs_resume():
        checkpoint = ctx.cognitive_state.resume_from or "unknown"
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Session Resume (resume: checkpoint={checkpoint})\n"
            "Returning from interruption. Protocol:\n"
            "1. State what was in progress at checkpoint\n"
            "2. Summarize any partial results\n"
            "3. Present single next action to continue\n"
            "4. Do NOT restart from scratch\n"
        )
    return result


def sk_micro(ctx: HookContext) -> HookResult:
    """micro-step: Micro-action decomposition for low-energy states."""
    result = HookResult()
    energy = ctx.cognitive_state.energy_level
    if energy == "low" and ctx.cognitive_state.task_tier_num >= 3:
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Micro-Action Mode (micro-step: active)\n"
            "Task tier exceeds low-energy capacity. Decompose:\n"
            "- Extract the single smallest actionable step\n"
            "- Present ONLY that step\n"
            "- Queue remainder for when capacity recovers\n"
            "- State what is deferred and why\n"
        )
    return result


def sk_anchor(ctx: HookContext) -> HookResult:
    """anchor: Context anchoring for monotropism contract.

    Enhanced: Maintains topic stack with recency tracking, attention decay
    calculation, and deferred topic queue.
    """
    result = HookResult()
    if not ctx.cognitive_state.active_thread:
        return result

    anchor_lines = [
        f"\n\n## Context Anchor (anchor: thread={ctx.cognitive_state.active_thread})",
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
    """code-review: Code review quality gate."""
    result = HookResult()
    if ctx.cognitive_state.active_mode in ("review", "rewrite") and ctx.options.get("code_review"):
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Code Review Gate (code-review)\n"
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
    """refocus: Refocus to declared objective when output drifts."""
    result = HookResult()
    if ctx.options.get("nudge_target"):
        target = ctx.options["nudge_target"]
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Refocus (refocus: target={target})\n"
            "Previous output drifted from objective. Correct course:\n"
            f"- Primary objective: {target}\n"
            "- Discard tangential content\n"
            "- Produce targeted output only\n"
        )
    return result


def sk_a11y(ctx: HookContext) -> HookResult:
    """accessibility: Accessibility compliance checker."""
    result = HookResult()
    if ctx.options.get("a11y_check") or ctx.cognitive_state.active_mode == "design":
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Accessibility Check (accessibility)\n"
            "Verify output meets accessibility standards:\n"
            "- Alt text for any visual content\n"
            "- Semantic structure (headings, lists) over visual formatting\n"
            "- Color is never the sole differentiator\n"
            "- Plain language preferred over jargon\n"
            "- Screen reader compatibility considered\n"
        )
    return result


def sk_sys_audit(ctx: HookContext) -> HookResult:
    """system-audit: System-level audit trigger for T4+."""
    result = HookResult()
    if ctx.cognitive_state.task_tier_num >= 4:
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## System Audit (system-audit: T4+)\n"
            "Meta-layer reflex required:\n"
            "- What objective function is this system optimizing?\n"
            "- What constraints are active vs. assumed?\n"
            "- What incentives might distort the output?\n"
            "- What failure modes exist?\n"
            "- What measurement would validate correctness?\n"
        )
    return result


def sk_sys_recover(ctx: HookContext) -> HookResult:
    """recover: System recovery from failures."""
    result = HookResult()
    if ctx.options.get("recovery_from"):
        error_info = ctx.options["recovery_from"]
        result.modified_prompt = (ctx.prompt or "") + (
            f"\n\n## Recovery Mode (recover)\n"
            f"Previous failure: {error_info}\n"
            "Recovery protocol:\n"
            "1. State the incorrect element and root cause\n"
            "2. Assess impact scope\n"
            "3. Produce corrected output\n"
            "4. Include revert path if correction fails\n"
        )
    return result


# ===========================================================================
# Enhanced speech-input: Speech-to-Text Preprocessing (v2)
# ===========================================================================

# Common STT misrecognitions in technical/AuDHD context
_STT_CORRECTIONS: dict[str, str] = {
    # Technical homophones
    "cash": "cache",
    "sequel": "SQL",
    "jason": "JSON",
    "pipe on": "Python",
    "pie thon": "Python",
    "no js": "Node.js",
    "node js": "Node.js",
    "react js": "React.js",
    "j query": "jQuery",
    "get hub": "GitHub",
    "get lab": "GitLab",
    "doctor": "Docker",
    "cube ctl": "kubectl",
    "cube control": "kubectl",
    "post gress": "Postgres",
    "my sequel": "MySQL",
    "redis": "Redis",
    "pie test": "pytest",
    "pie pie": "PyPI",
    "npm": "npm",
    "api": "API",
    "gpu": "GPU",
    "cpu": "CPU",
    "ess ess h": "SSH",
    "h t t p": "HTTP",
    "h t t p s": "HTTPS",
    "you are l": "URL",
    "rest api": "REST API",
    "graph ql": "GraphQL",
    # AuDHD/cognitive terms
    "mono tropism": "monotropism",
    "executive function": "executive function",
    "hyper focus": "hyperfocus",
    "hyper fixation": "hyperfixation",
    "stim": "stim",
    "masking": "masking",
    # Swarm model names (readable)
    "g pro 31": "gemini-2.5-pro",
    "g flash 31": "gemini-2.5-flash",
    "o 4 mini": "o4-mini",
    "o 54": "o1",
    "claude": "Claude",
    "gemini": "Gemini",
}

# Filler words to strip (context-aware: some preserved in specific positions)
_STT_FILLERS: set[str] = {
    "um", "uh", "erm", "hmm", "hm",
    "basically", "honestly", "literally",
}

# Context-dependent fillers: only strip when NOT in these contexts
_STT_CONDITIONAL_FILLERS: dict[str, Callable[[list[str], int], bool]] = {
    "like": lambda words, i: not (
        # Preserve in comparisons: "looks like", "feels like", "something like"
        (i > 0 and words[i - 1].lower() in ("looks", "feels", "seems", "something", "more", "just"))
        # Preserve in similes: "like a", "like the"
        or (i + 1 < len(words) and words[i + 1].lower() in ("a", "an", "the", "this", "that"))
    ),
    "right": lambda words, i: not (
        # Preserve in confirmations: "that's right", "right here", "right now"
        (i > 0 and words[i - 1].lower() in ("that's", "thats", "is"))
        or (i + 1 < len(words) and words[i + 1].lower() in ("here", "now", "there", "away", "side"))
    ),
    "so": lambda words, i: not (
        # Preserve causal 'so': "so that", "so it", or mid-sentence
        i > 0  # Only strip sentence-initial 'so'
    ),
    "you know": lambda words, i: False,  # Always strip
    "i mean": lambda words, i: not (
        # Preserve when correcting: "I mean [different thing]"
        i + 2 < len(words)  # If followed by content, likely a correction
    ),
    "actually": lambda words, i: not (
        # Preserve when introducing a correction
        i > 0  # Only strip sentence-initial 'actually' with no prior context
    ),
}

# Topic shift signal words (ordered by specificity, most specific first)
_STT_SHIFT_SIGNALS: list[str] = [
    "oh one more thing",
    "before i forget",
    "switching gears",
    "different topic",
    "unrelated but",
    "on a tangent",
    "quick sidebar",
    "oh and also",
    "come to think of it",
    "while i'm at it",
    "oh wait",
    "sidebar",
    "tangent",
]


def _stt_correct_misrecognitions(text: str) -> tuple[str, int]:
    """Apply STT misrecognition corrections. Returns (corrected, count)."""
    corrected = text
    count = 0
    for wrong, right in _STT_CORRECTIONS.items():
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        matches = pattern.findall(corrected)
        if matches:
            corrected = pattern.sub(right, corrected)
            count += len(matches)
    return corrected, count


def _stt_dedup_repeated_phrases(text: str) -> tuple[str, int]:
    """Remove repeated phrases (stutters, restart loops).

    Detects patterns like:
    - "the thing is the thing is" -> "the thing is"
    - "I want to I want to fix" -> "I want to fix"
    """
    dedup_count = 0
    # Match 2-6 word phrases repeated immediately
    for phrase_len in range(6, 1, -1):
        pattern = re.compile(
            r"\b((?:\w+\s+){" + str(phrase_len - 1) + r"}\w+)\s+\1\b",
            re.IGNORECASE,
        )
        while pattern.search(text):
            text = pattern.sub(r"\1", text)
            dedup_count += 1
    return text, dedup_count


def _stt_repair_sentence_boundaries(text: str) -> str:
    """Repair missing punctuation from STT output.

    STT engines often drop periods, producing run-on sentences.
    Heuristic: if a lowercase word follows a word that looks like
    a sentence ending (verb, complete thought), insert a period.
    """
    # Add period before clear new-sentence signals
    text = re.sub(
        r"(\w)\s+(I\s+(?:need|want|think|should|was|am|have|will|can)\b)",
        r"\1. \2",
        text,
    )
    # Add period before "can you", "could you", "please"
    text = re.sub(
        r"(\w)\s+((?:can|could|would|should)\s+you\b)",
        r"\1. \2",
        text,
    )
    return text


def _stt_filter_fillers_contextual(words: list[str]) -> tuple[list[str], int]:
    """Context-aware filler removal. Returns (filtered_words, removed_count)."""
    filtered: list[str] = []
    removed = 0
    skip_next = False

    for i, word in enumerate(words):
        if skip_next:
            skip_next = False
            continue

        lower = word.lower().strip(".,!?;:")

        # Check two-word fillers first
        if i + 1 < len(words):
            bigram = f"{lower} {words[i + 1].lower().strip('.,!?;:')}"
            if bigram in _STT_CONDITIONAL_FILLERS:
                should_strip = _STT_CONDITIONAL_FILLERS[bigram](words, i)
                if should_strip:
                    removed += 2
                    skip_next = True
                    continue

        # Check single-word unconditional fillers
        if lower in _STT_FILLERS:
            removed += 1
            continue

        # Check single-word conditional fillers
        if lower in _STT_CONDITIONAL_FILLERS:
            should_strip = _STT_CONDITIONAL_FILLERS[lower](words, i)
            if should_strip:
                removed += 1
                continue

        filtered.append(word)

    return filtered, removed


def _stt_detect_topic_shifts(text: str) -> tuple[str, list[str]]:
    """Detect multiple topic shifts, extract deferred topics."""
    deferred: list[str] = []
    remaining = text

    for signal in _STT_SHIFT_SIGNALS:
        if signal.lower() in remaining.lower():
            parts = re.split(
                re.escape(signal), remaining, maxsplit=1, flags=re.IGNORECASE
            )
            if len(parts) == 2 and parts[1].strip():
                deferred.append(parts[1].strip())
                remaining = parts[0].strip()
                # Continue checking the deferred part for nested shifts
                for nested_signal in _STT_SHIFT_SIGNALS:
                    if nested_signal.lower() in deferred[-1].lower():
                        nested_parts = re.split(
                            re.escape(nested_signal),
                            deferred[-1],
                            maxsplit=1,
                            flags=re.IGNORECASE,
                        )
                        if len(nested_parts) == 2 and nested_parts[1].strip():
                            deferred[-1] = nested_parts[0].strip()
                            deferred.append(nested_parts[1].strip())
                        break
                break  # Only process outermost shift in primary text

    return remaining, deferred


def _stt_split_compressed_burst(text: str) -> list[str]:
    """Split compressed multi-intent utterances into individual intents."""
    # Action verb patterns that signal intent boundaries
    intent_splitters = re.compile(
        r"\b(?:"
        r"and\s+(?:then\s+)?(?:also\s+)?(?:can\s+you\s+|please\s+|could\s+you\s+)?"
        r"|also\s+(?:can\s+you\s+|please\s+|could\s+you\s+)?"
        r"|then\s+(?:can\s+you\s+|please\s+|could\s+you\s+)?"
        r"|plus\s+(?:can\s+you\s+|please\s+|could\s+you\s+)?"
        r"|oh\s+and\s+"
        r")",
        re.IGNORECASE,
    )
    intents = intent_splitters.split(text)
    return [i.strip() for i in intents if i.strip() and len(i.strip()) > 3]


def sk_stt(ctx: HookContext) -> HookResult:
    """speech-input: Speech-to-text preprocessing for AuDHD speech patterns (v2).

    Pre-execute hook with full processing pipeline:
    1. Misrecognition correction (technical terms, model names)
    2. Repeated phrase deduplication (stutters, restart loops)
    3. False start removal ("I need to... wait, actually...")
    4. Context-aware filler filtering (preserves semantic fillers)
    5. Sentence boundary repair (missing punctuation from STT)
    6. Topic shift detection with nested shift support
    7. Compressed burst splitting (multi-intent utterances)
    8. Confidence scoring + cleanup metrics
    """
    result = HookResult()
    raw = ctx.options.get("stt_raw_transcript")
    if not raw:
        return result

    energy = ctx.cognitive_state.energy_level
    e_key = energy.value if hasattr(energy, "value") else str(energy)
    text = raw.strip()
    original_word_count = len(text.split())

    # Crash mode: pass through unchanged, minimal processing
    if e_key == "crash":
        result.modified_input = text
        return result

    stt_flags: list[str] = []
    deferred_topics: list[str] = []
    metrics: dict[str, Any] = {"original_length": len(text), "original_words": original_word_count}

    # --- Stage 1: Misrecognition correction ---
    text, correction_count = _stt_correct_misrecognitions(text)
    if correction_count > 0:
        metrics["corrections"] = correction_count

    # --- Stage 2: Repeated phrase deduplication ---
    text, dedup_count = _stt_dedup_repeated_phrases(text)
    if dedup_count > 0:
        stt_flags.append("STT-STUTTER")
        metrics["dedup_count"] = dedup_count

    # --- Stage 3: False start removal ---
    restart_pattern = re.compile(
        r"(?:I\s+(?:need|want|was|should|think|started|tried)\s+to\s+)?"
        r"(?:\.{2,}|,)?\s*"
        r"(?:wait|no|actually|sorry|let me (?:restart|start over|rephrase|think))"
        r"[,.]?\s*",
        re.IGNORECASE,
    )
    restart_matches = restart_pattern.findall(text)
    if restart_matches:
        stt_flags.append("STT-RESTART")
        text = restart_pattern.sub("", text).strip()
        metrics["false_starts"] = len(restart_matches)

    # --- Stage 4: Context-aware filler filtering ---
    words = text.split()
    filtered_words, filler_count = _stt_filter_fillers_contextual(words)
    if filler_count > 0:
        metrics["fillers_removed"] = filler_count
        filler_ratio = filler_count / max(len(words), 1)
        if filler_ratio > 0.3:
            stt_flags.append("STT-FILLER-HEAVY")
    text = " ".join(filtered_words)

    # --- Stage 5: Sentence boundary repair ---
    text = _stt_repair_sentence_boundaries(text)

    # --- Stage 6: Topic shift detection ---
    text, shift_topics = _stt_detect_topic_shifts(text)
    if shift_topics:
        deferred_topics.extend(shift_topics)
        stt_flags.append("STT-TOPIC-SHIFT")
        metrics["topic_shifts"] = len(shift_topics)

    # --- Stage 7: Compressed burst splitting ---
    intents = _stt_split_compressed_burst(text)
    if len(intents) > 1:
        stt_flags.append("STT-MULTI-INTENT")
        metrics["intent_count"] = len(intents)
        if e_key == "low":
            # Low energy: take first intent only, defer rest
            deferred_topics.extend(intents[1:])
            text = intents[0]
        elif e_key == "medium":
            # Medium energy: take first 2, defer rest
            deferred_topics.extend(intents[2:])
            text = ". ".join(intents[:2])
        # High energy: keep all intents

    # --- Stage 8: Confidence scoring ---
    final_word_count = len(text.split())
    cleanup_ratio = 1.0 - (final_word_count / max(original_word_count, 1))
    # Confidence: high if little cleanup needed, low if heavy modification
    confidence = max(0.1, 1.0 - (cleanup_ratio * 1.5))
    confidence = min(1.0, confidence)
    if len(stt_flags) >= 3:
        confidence *= 0.8  # Multiple issues lower confidence
    metrics["cleanup_ratio"] = round(cleanup_ratio, 3)
    metrics["confidence"] = round(confidence, 3)
    metrics["final_words"] = final_word_count

    if confidence < 0.5:
        stt_flags.append("STT-LOW-CONFIDENCE")

    # --- Store results ---
    result.modified_input = text.strip()
    result.modified_options = {}
    if deferred_topics:
        result.modified_options["deferred_topics"] = deferred_topics
    if stt_flags:
        result.modified_options["stt_flags"] = stt_flags
    result.modified_options["stt_metrics"] = metrics
    result.modified_options["stt_confidence"] = confidence
    result.modified_options["stt_original"] = raw  # Preserve raw for audit

    return result


# ===========================================================================
# Enhanced speech-output: Text-to-Speech Output Routing (v2)
# ===========================================================================

# Voice parameter presets by energy level
_TTS_VOICE_PARAMS: dict[str, dict[str, float]] = {
    "high":   {"rate": 1.0,  "volume": 0.8, "pause_multiplier": 1.0,  "pitch_semitones": 0.0},
    "medium": {"rate": 0.95, "volume": 0.8, "pause_multiplier": 1.1,  "pitch_semitones": -0.5},
    "low":    {"rate": 0.85, "volume": 0.7, "pause_multiplier": 1.25, "pitch_semitones": -1.0},
    "crash":  {"rate": 0.75, "volume": 0.6, "pause_multiplier": 1.5,  "pitch_semitones": -1.5},
}

# Max output items by energy
_TTS_MAX_ITEMS: dict[str, int] = {
    "high": 999, "medium": 10, "low": 3, "crash": 1,
}

# Max output sentences by energy
_TTS_MAX_SENTENCES: dict[str, int] = {
    "high": 999, "medium": 20, "low": 5, "crash": 1,
}

# Pronunciation hints for technical terms
_TTS_PRONUNCIATION: dict[str, str] = {
    "API": "A P I",
    "APIs": "A P I s",
    "SQL": "S Q L",
    "JSON": "jay-son",
    "CLI": "C L I",
    "GUI": "gooey",
    "URL": "U R L",
    "URLs": "U R L s",
    "HTTP": "H T T P",
    "HTTPS": "H T T P S",
    "SSH": "S S H",
    "GPU": "G P U",
    "CPU": "C P U",
    "npm": "N P M",
    "PyPI": "pie-pie",
    "pytest": "pie-test",
    "stdin": "standard in",
    "stdout": "standard out",
    "stderr": "standard error",
    "regex": "reg-ex",
    "kubectl": "cube-control",
    "nginx": "engine-x",
    "char": "care",
    "deque": "deck",
    "tuple": "tupple",
    "AuDHD": "aw-D-H-D",
    "ADHD": "A-D-H-D",
    "OSINT": "oh-sint",
    "SSML": "S S M L",
    "Pydantic": "pie-dantic",
    "FastAPI": "fast A P I",
}

# Content type detection patterns
_TTS_CONTENT_PATTERNS: dict[str, re.Pattern] = {
    "code": re.compile(r"```|`[^`]+`|def\s+\w+|class\s+\w+|import\s+\w+|\bfunction\b"),
    "table": re.compile(r"\|.*\|.*\||<table|<tr|<td"),
    "list": re.compile(r"^\s*[-*]\s+|^\s*\d+\.\s+", re.MULTILINE),
    "verdict": re.compile(r"\*\*(?:FIXED|DONE|PASS|FAIL|BLOCKED|CRITICAL|HIGH|LOW|MEDIUM)\*\*"),
    "claim_tagged": re.compile(r"\[(?:observed|inferred|general|unverified)\]"),
}


def _tts_detect_content_type(text: str) -> list[str]:
    """Detect content types present in the text."""
    detected: list[str] = []
    for ctype, pattern in _TTS_CONTENT_PATTERNS.items():
        if pattern.search(text):
            detected.append(ctype)
    if not detected:
        detected.append("narrative")
    return detected


def _tts_estimate_duration(text: str, rate: float, pause_mult: float) -> float:
    """Estimate speech duration in seconds.

    Average English speech: ~150 words/minute.
    Adjusted for rate and pauses.
    """
    word_count = len(text.split())
    base_wpm = 150 * rate
    base_duration = (word_count / base_wpm) * 60

    # Count natural pause points
    sentence_count = len(re.findall(r"[.!?]+", text))
    header_count = len(re.findall(r"^#{1,4}\s", text, re.MULTILINE))
    paragraph_breaks = text.count("\n\n")

    pause_seconds = (
        (sentence_count * 0.3 * pause_mult)
        + (header_count * 0.8 * pause_mult)
        + (paragraph_breaks * 1.0 * pause_mult)
    )

    return round(base_duration + pause_seconds, 1)


def _tts_generate_ssml_hints(text: str, params: dict[str, float]) -> dict[str, Any]:
    """Generate SSML directive hints for downstream TTS engine.

    Does NOT produce raw SSML (that's engine-specific). Produces a
    structured hint object the TTS engine adapter can consume.
    """
    hints: dict[str, Any] = {
        "prosody": {
            "rate": f"{int(params['rate'] * 100)}%",
            "volume": f"{int(params['volume'] * 100)}%",
            "pitch": f"{params.get('pitch_semitones', 0):+.1f}st",
        },
        "breaks": [],
        "emphasis": [],
        "say_as": [],
    }

    # Break hints at topic boundaries
    for match in re.finditer(r"^#{1,4}\s+(.+)$", text, re.MULTILINE):
        hints["breaks"].append({
            "before": match.group(1),
            "strength": "strong",
            "duration_ms": int(500 * params.get("pause_multiplier", 1.0)),
        })

    # Emphasis on bold text (verdict-first pattern)
    for match in re.finditer(r"\*\*([^*]+)\*\*", text):
        hints["emphasis"].append({
            "text": match.group(1),
            "level": "strong",
        })

    # Pronunciation hints for technical terms
    for term, pronunciation in _TTS_PRONUNCIATION.items():
        if term in text:
            hints["say_as"].append({
                "text": term,
                "interpret_as": "characters" if len(term) <= 4 and term.isupper() else "name",
                "pronunciation": pronunciation,
            })

    return hints


def _tts_build_content_directives(content_types: list[str], e_key: str) -> list[str]:
    """Build content-type-specific speech directives."""
    directives: list[str] = []

    if "code" in content_types:
        directives.extend([
            "- Code blocks: Describe purpose in plain language, do NOT read syntax character by character",
            "- For short snippets (<3 lines): read key identifiers and flow",
            "- For long blocks: summarize structure and key logic only",
            "- Variable names: spell out or use natural pronunciation",
        ])

    if "table" in content_types:
        directives.extend([
            "- Tables: Convert to ranked comparisons or sequential descriptions",
            "- Pattern: 'The first option is [X], which has [property]. The second option is [Y]...'",
            "- For large tables (4+ rows): summarize top 3, mention total count",
        ])

    if "list" in content_types:
        max_items = _TTS_MAX_ITEMS.get(e_key, 10)
        directives.extend([
            f"- Lists: Read up to {max_items} items, state count if truncated",
            "- Nested lists: Flatten with depth cues ('Under the first point...')",
            "- Number items explicitly when order matters",
        ])

    if "verdict" in content_types:
        directives.extend([
            "- Verdicts: Lead with the verdict, emphasize status (FIXED, CRITICAL, etc.)",
            "- Pause briefly after the verdict before supporting detail",
        ])

    if "claim_tagged" in content_types:
        directives.extend([
            "- Claim tags vocalized: [observed]=(read as-is), [inferred]='This is inferred:',",
            "  [unverified]='This is unverified:', [general]=(omit, treat as default)",
        ])

    if "narrative" in content_types and len(content_types) == 1:
        directives.append("- Narrative text: natural reading pace, emphasize key terms")

    return directives


def sk_tts(ctx: HookContext) -> HookResult:
    """speech-output: Text-to-speech output routing (v2).

    Enhanced post-execute style hook with:
    - Content type detection (code, table, list, verdict, claim_tagged, narrative)
    - Type-specific speech directives
    - SSML hint generation for downstream TTS engines
    - Duration estimation
    - Pronunciation hints for technical terms
    - Energy-adaptive chunking with natural break points
    """
    result = HookResult()
    if not ctx.options.get("tts_enabled"):
        return result

    energy = ctx.cognitive_state.energy_level
    e_key = energy.value if hasattr(energy, "value") else str(energy)
    params = _TTS_VOICE_PARAMS.get(e_key, _TTS_VOICE_PARAMS["medium"])
    max_sentences = _TTS_MAX_SENTENCES.get(e_key, 20)

    # Detect content types in current prompt/context
    sample_text = ctx.input_text + "\n" + (ctx.prompt or "")
    content_types = _tts_detect_content_type(sample_text)

    # Build directives
    tts_lines = [
        f"\n\n## Speech Output Mode (speech-output v2: {e_key}, types={','.join(content_types)})",
        "Output will be consumed as audio. Adapt for spoken delivery:",
        "",
        "### Structure Adaptation",
        "- Replace headers with spoken transitions ('Moving to...', 'Next:')",
        "- Split compound sentences at conjunctions for breath points",
        "- Expand abbreviations on first use",
        f"- Maximum {max_sentences} sentences total",
        "",
        "### Content-Specific Rules",
    ]
    tts_lines.extend(_tts_build_content_directives(content_types, e_key))

    # Energy overrides
    if e_key == "crash":
        tts_lines.extend(["", "### CRASH OVERRIDE", "Single sentence. No structure. State only."])
    elif e_key == "low":
        tts_lines.extend(["", "### LOW ENERGY", "Maximum 3 short sentences. Verdict only."])

    # Pronunciation section (if technical terms detected)
    found_terms = [t for t in _TTS_PRONUNCIATION if t in sample_text]
    if found_terms:
        tts_lines.extend(["", "### Pronunciation Guide"])
        for term in found_terms[:10]:
            tts_lines.append(f"- {term}: {_TTS_PRONUNCIATION[term]}")

    # Duration estimate
    est_duration = _tts_estimate_duration(sample_text, params["rate"], params["pause_multiplier"])

    # SSML hints
    ssml_hints = _tts_generate_ssml_hints(sample_text, params)

    # Store in options for downstream
    result.modified_options = {
        "tts_voice_params": params,
        "tts_content_types": content_types,
        "tts_estimated_duration_sec": est_duration,
        "tts_ssml_hints": ssml_hints,
        "tts_max_sentences": max_sentences,
    }

    result.modified_prompt = (ctx.prompt or "") + "\n".join(tts_lines)
    return result


# ===========================================================================
# Enhanced tone: Tone and Register Adaptation (v2)
# ===========================================================================

# Full tone matrix with numeric personality/density scores
_TONE_MATRIX: dict[str, dict[str, Any]] = {
    "execute":      {"register": "technical_direct",     "density": 1.0,  "formality": 0.3, "personality": 0.1, "valence": "neutral"},
    "draft":        {"register": "audience_matched",     "density": 0.7,  "formality": 0.5, "personality": 0.5, "valence": "neutral"},
    "rewrite":      {"register": "source_matched",       "density": 0.8,  "formality": 0.5, "personality": 0.1, "valence": "neutral"},
    "review":       {"register": "analytical_precise",   "density": 0.9,  "formality": 0.6, "personality": 0.1, "valence": "critical"},
    "decide":       {"register": "neutral_balanced",     "density": 0.9,  "formality": 0.5, "personality": 0.1, "valence": "neutral"},
    "troubleshoot": {"register": "terse_action",         "density": 1.0,  "formality": 0.2, "personality": 0.0, "valence": "urgent"},
    "design":       {"register": "architectural_precise", "density": 0.9, "formality": 0.5, "personality": 0.1, "valence": "neutral"},
    "summarize":    {"register": "dense_verdict",        "density": 1.0,  "formality": 0.3, "personality": 0.1, "valence": "neutral"},
    "osint":        {"register": "clinical_tagged",      "density": 1.0,  "formality": 0.8, "personality": 0.0, "valence": "clinical"},
    "chat":         {"register": "conversational",       "density": 0.5,  "formality": 0.2, "personality": 0.6, "valence": "warm"},
}

# Compound mode blending rules (when two modes co-occur)
_TONE_COMPOUND_MODES: dict[tuple[str, str], dict[str, Any]] = {
    ("review", "draft"):       {"register": "analytical_constructive", "density": 0.85, "formality": 0.5, "personality": 0.2, "valence": "critical"},
    ("design", "execute"):     {"register": "architectural_action",   "density": 0.95, "formality": 0.4, "personality": 0.1, "valence": "neutral"},
    ("summarize", "review"):   {"register": "dense_analytical",       "density": 1.0,  "formality": 0.5, "personality": 0.1, "valence": "critical"},
    ("troubleshoot", "design"): {"register": "diagnostic_architectural", "density": 1.0, "formality": 0.4, "personality": 0.0, "valence": "urgent"},
    ("draft", "chat"):         {"register": "casual_creative",       "density": 0.5,  "formality": 0.2, "personality": 0.7, "valence": "warm"},
}

_TONE_AUDIENCE: dict[str, dict[str, Any]] = {
    "technical":  {"directive": "Jargon allowed. Assume domain fluency. No hand-holding.",                "formality_mod": 0.0, "density_mod": 0.0},
    "executive":  {"directive": "Lead with impact and business outcomes. Minimize implementation detail.", "formality_mod": 0.2, "density_mod": -0.1},
    "client":     {"directive": "Professional. No internal references. Action-oriented deliverables.",    "formality_mod": 0.3, "density_mod": -0.1},
    "peer":       {"directive": "Direct. Skip shared context. No social scaffolding.",                   "formality_mod": 0.0, "density_mod": 0.0},
    "public":     {"directive": "Accessible language. Define terms. No domain assumptions.",              "formality_mod": 0.1, "density_mod": -0.3},
    "self":       {"directive": "Maximum compression. Shorthand OK. No social scaffolding.",              "formality_mod": -0.2, "density_mod": 0.2},
    "instructor": {"directive": "Teaching register. Build from foundations. Verify understanding.",        "formality_mod": 0.1, "density_mod": -0.2},
    "regulator":  {"directive": "Formal, precise, auditable. Cite standards. No ambiguity.",              "formality_mod": 0.4, "density_mod": -0.1},
}

# Audience inference signals (when audience isn't explicitly set)
_TONE_AUDIENCE_SIGNALS: dict[str, list[str]] = {
    "technical":  ["code", "function", "class", "deploy", "schema", "runtime", "API", "debug"],
    "executive":  ["ROI", "revenue", "stakeholder", "quarterly", "roadmap", "KPI", "OKR"],
    "client":     ["deliverable", "timeline", "scope", "invoice", "contract", "proposal"],
    "instructor": ["lesson", "module", "student", "learning", "curriculum", "assessment"],
    "public":     ["blog", "audience", "readers", "explain", "introduction", "overview"],
}

# Emotional valence detection
_TONE_VALENCE_SIGNALS: dict[str, list[str]] = {
    "negative": ["error", "fail", "broken", "crash", "bug", "issue", "problem", "critical", "blocker"],
    "positive": ["fixed", "done", "complete", "passed", "success", "resolved", "shipped"],
    "urgent":   ["urgent", "ASAP", "immediately", "blocking", "production", "outage", "down"],
}

# Expanded blocked patterns with categories
_TONE_BLOCKED: dict[str, list[str]] = {
    "corporate_jargon": [
        "synergy", "leverage", "circle back", "touch base", "deep dive",
        "move the needle", "low-hanging fruit", "bandwidth", "pivot",
        "take offline", "level set", "loop in", "double click on",
        "open the kimono", "boil the ocean", "paradigm shift",
        "at the end of the day", "value add", "best of breed",
        "net net", "run it up the flagpole",
    ],
    "hedging": [
        "i think maybe", "it might be possible that", "perhaps we could consider",
        "i'm not sure but", "it seems like it could be",
        "there's a chance that", "arguably",
    ],
    "performative": [
        "hope this helps", "happy to help", "great question",
        "thanks for asking", "that's a really good point",
        "absolutely", "definitely", "of course",
    ],
    "caretaker": [
        "take care of yourself", "don't worry", "it's okay",
        "be gentle with yourself", "you've got this",
        "i believe in you", "sending good vibes",
        "remember to breathe", "you're doing great",
    ],
}


def _tone_infer_audience(text: str) -> str | None:
    """Infer audience from content signals when not explicitly set."""
    scores: dict[str, int] = {}
    text_lower = text.lower()
    for audience, signals in _TONE_AUDIENCE_SIGNALS.items():
        score = sum(1 for s in signals if s.lower() in text_lower)
        if score > 0:
            scores[audience] = score
    if not scores:
        return None
    return max(scores, key=scores.get)


def _tone_detect_valence(text: str) -> str:
    """Detect emotional valence of content for register calibration."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for valence, signals in _TONE_VALENCE_SIGNALS.items():
        score = sum(1 for s in signals if s in text_lower)
        if score > 0:
            scores[valence] = score
    if not scores:
        return "neutral"
    return max(scores, key=scores.get)


def _tone_resolve_compound(mode: str, secondary_mode: str | None) -> dict[str, Any] | None:
    """Resolve compound mode tone by blending two modes."""
    if not secondary_mode or secondary_mode == mode:
        return None
    # Check pre-defined compounds (both orderings)
    compound = _TONE_COMPOUND_MODES.get((mode, secondary_mode))
    if compound:
        return compound
    compound = _TONE_COMPOUND_MODES.get((secondary_mode, mode))
    if compound:
        return compound
    # Auto-blend: average the numeric scores, take primary's register
    primary = _TONE_MATRIX.get(mode)
    secondary = _TONE_MATRIX.get(secondary_mode)
    if primary and secondary:
        return {
            "register": f"{primary['register']}+{secondary['register']}",
            "density": (primary["density"] + secondary["density"]) / 2,
            "formality": (primary["formality"] + secondary["formality"]) / 2,
            "personality": min(primary["personality"], secondary["personality"]),
            "valence": primary["valence"],
        }
    return None


def _tone_get_blocked_flat() -> list[str]:
    """Get flattened list of all blocked patterns."""
    return [p for patterns in _TONE_BLOCKED.values() for p in patterns]


def sk_tone(ctx: HookContext) -> HookResult:
    """tone: Tone and register adaptation by mode and audience (v2).

    Enhanced zero-cost prompt injection with:
    - Compound mode blending (review+draft, design+execute, etc.)
    - Audience inference from content signals when not explicitly set
    - Emotional valence detection (don't use upbeat tone for error reports)
    - Tone transition markers for multi-section output
    - Extended blocked patterns (corporate, hedging, performative, caretaker)
    - Numeric density/formality/personality scoring for fine control
    """
    result = HookResult()
    mode = ctx.cognitive_state.active_mode
    energy = ctx.cognitive_state.energy_level
    e_key = energy.value if hasattr(energy, "value") else str(energy)

    # Crash mode: no tone processing overhead
    if e_key == "crash":
        return result

    # --- Resolve tone (single or compound mode) ---
    secondary_mode = ctx.options.get("secondary_mode")
    compound_tone = _tone_resolve_compound(mode, secondary_mode)
    tone = compound_tone or _TONE_MATRIX.get(mode, _TONE_MATRIX["execute"])
    compound_label = f" (compound: {mode}+{secondary_mode})" if compound_tone else ""

    # --- Audience resolution ---
    explicit_audience = ctx.options.get("audience")
    if explicit_audience:
        audience = explicit_audience
        audience_source = "explicit"
    else:
        inferred = _tone_infer_audience(ctx.input_text)
        audience = inferred or "self"
        audience_source = f"inferred:{inferred}" if inferred else "default"

    audience_config = _TONE_AUDIENCE.get(audience, _TONE_AUDIENCE["self"])

    # --- Emotional valence ---
    content_valence = _tone_detect_valence(ctx.input_text)
    mode_valence = tone.get("valence", "neutral")
    # Use content valence if it's stronger than mode default
    effective_valence = content_valence if content_valence != "neutral" else mode_valence

    # --- Compute effective scores ---
    density = min(1.0, max(0.0, tone["density"] + audience_config["density_mod"]))
    formality = min(1.0, max(0.0, tone["formality"] + audience_config["formality_mod"]))
    personality = tone["personality"]

    # Energy overrides on scores
    if e_key == "low":
        density = min(density, 0.8)
        personality = 0.0
        formality = min(formality, 0.3)
    elif e_key == "medium":
        personality = min(personality, 0.3)

    # Formality override from options
    formality_override = ctx.options.get("formality_override")
    if formality_override:
        formality_map = {"formal": 0.8, "neutral": 0.5, "casual": 0.2}
        formality = formality_map.get(formality_override, formality)

    # --- Build directive ---
    tone_lines = [
        f"\n\n## Tone Directive (tone v2: {tone['register']}{compound_label})",
        f"Audience: {audience} ({audience_source}). {audience_config['directive']}",
        f"Scores: density={density:.1f}, formality={formality:.1f}, personality={personality:.1f}",
        f"Valence: {effective_valence}",
    ]

    # Valence-specific guidance
    if effective_valence == "negative" or effective_valence == "critical":
        tone_lines.append("Tone: matter-of-fact. No sugar-coating. No upbeat framing for problems.")
    elif effective_valence == "urgent":
        tone_lines.append("Tone: urgent, action-first. Skip context. Lead with what to do NOW.")
    elif effective_valence == "warm":
        tone_lines.append("Tone: conversational. Personality allowed. Match user's energy.")
    elif effective_valence == "clinical":
        tone_lines.append("Tone: clinical precision. Zero personality. Data only.")

    # Energy adjustments
    if e_key == "low":
        tone_lines.append("")
        tone_lines.append("LOW ENERGY OVERRIDE: Bare minimum. Direct answers only. Zero social scaffolding.")

    # Tone transitions for multi-section output
    if ctx.options.get("multi_section"):
        tone_lines.extend([
            "",
            "### Tone Transitions",
            "- Announce section transitions naturally ('Next:', 'Moving to...')",
            "- Maintain consistent register across sections",
            "- If sections have different audiences, note the shift",
        ])

    # Blocked patterns (categorized)
    tone_lines.extend(["", "### Blocked Patterns"])
    for category, patterns in _TONE_BLOCKED.items():
        sample = ", ".join(f"'{p}'" for p in patterns[:4])
        tone_lines.append(f"- {category}: {sample}, etc.")

    # Post-validation hint
    tone_lines.extend([
        "",
        "### Self-Check",
        "Before finalizing: scan output for any blocked pattern.",
        f"Verify register is consistently {tone['register']}.",
        f"Verify density target ({density:.1f}) is met (no padding if >0.7).",
    ])

    # Store computed tone metadata in options
    result.modified_options = {
        "tone_register": tone["register"],
        "tone_audience": audience,
        "tone_audience_source": audience_source,
        "tone_valence": effective_valence,
        "tone_density": density,
        "tone_formality": formality,
        "tone_personality": personality,
    }

    result.modified_prompt = (ctx.prompt or "") + "\n".join(tone_lines)
    return result


# ---------------------------------------------------------------------------
# Hook Registry
# ---------------------------------------------------------------------------

HOOK_REGISTRY: dict[str, Callable[[HookContext], HookResult]] = {
    # Original 6
    "decompose": sk_decomp,
    "bridge": sk_bridge,
    "quality-gate": sk_gate,
    "verify": sk_verify,
    "focus": sk_prioritize,
    "format": sk_format,
    # F2 additions
    "reality-check": sk_reality,
    "energy-route": sk_energy,
    "load-skill": sk_extern,
    "resume": sk_resume,
    "micro-step": sk_micro,
    "anchor": sk_anchor,
    "code-review": sk_codereview,
    "refocus": sk_nudge,
    "accessibility": sk_a11y,
    "system-audit": sk_sys_audit,
    "recover": sk_sys_recover,
    # Enhancements (v2)
    "speech-input": sk_stt,
    "speech-output": sk_tts,
    "tone": sk_tone,
}


def _build_sk_alias_map() -> dict[str, str]:
    """Build reverse map from SK-* YAML aliases to HOOK_REGISTRY keys.

    Skill YAMLs declare hooks as SK-GATE, SK-VERIFY, etc.  The registry
    keys are descriptive (quality-gate, verify, ...).  This map lets
    run_hooks() accept either format.
    """
    alias_map: dict[str, str] = {}
    for registry_key, fn in HOOK_REGISTRY.items():
        # fn.__name__ is e.g. "sk_gate" -> SK alias is "SK-GATE"
        sk_alias = "SK-" + fn.__name__.removeprefix("sk_").upper()
        alias_map[sk_alias] = registry_key
    return alias_map


_SK_ALIAS_MAP: dict[str, str] = {}  # populated lazily after registry is patched


def _resolve_hook_name(name: str) -> str:
    """Normalise a hook name: accept SK-* aliases or registry keys."""
    global _SK_ALIAS_MAP
    if not _SK_ALIAS_MAP:
        _SK_ALIAS_MAP = _build_sk_alias_map()
    return _SK_ALIAS_MAP.get(name, name)


def run_hooks(hook_names: list[str], ctx: HookContext) -> HookResult:
    """Execute hook chain in declared order, merging results.

    Always-on hooks (reality-check, energy-route) run first regardless of
    whether they appear in hook_names.

    Hook names may be registry keys (``quality-gate``) or SK-* aliases
    from skill YAML (``SK-GATE``).  Both are accepted.
    """
    # Prepend always-on hooks (deduplicate if already in list)
    effective_hooks = list(ALWAYS_ON_HOOKS)
    for name in hook_names:
        resolved = _resolve_hook_name(name)
        if resolved not in effective_hooks:
            effective_hooks.append(resolved)

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
