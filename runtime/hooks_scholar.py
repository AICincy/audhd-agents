"""SK-SCHOLAR (P2.7) + Context Monitoring Extensions (P2.5).

Grounded implementations per audit discussion constraints:
- Prompt-injection only (no independent action, no persistent listener)
- Augmentation for competent adults (not caretaker, not safety scaffolding)
- Knowledge injection from PROFILE.md (not supervisor, no inter-skill bus)
- Context monitoring via text heuristics (not ML inference, not streaming)

Integration:
    from runtime.hooks_scholar import patch_hook_registry
    patch_hook_registry(HOOK_REGISTRY, ALWAYS_ON_HOOKS)
"""

from __future__ import annotations

import re
from typing import Any, Callable

# Import from hooks.py (these are needed for type compatibility)
# Use string import to avoid circular dependency at module level
_HOOK_CONTEXT_TYPE = None
_HOOK_RESULT_TYPE = None


def _lazy_import():
    """Lazy import to avoid circular dependency with hooks.py."""
    global _HOOK_CONTEXT_TYPE, _HOOK_RESULT_TYPE
    if _HOOK_CONTEXT_TYPE is None:
        from runtime.hooks import HookContext, HookResult
        _HOOK_CONTEXT_TYPE = HookContext
        _HOOK_RESULT_TYPE = HookResult
    return _HOOK_CONTEXT_TYPE, _HOOK_RESULT_TYPE


# ===========================================================================
# P2.5: Context Monitoring Helpers
# ===========================================================================
# These detect conversation signals via text heuristics.
# [GROUNDED] Regex + arithmetic. No ML models. No external APIs.
# [NOT FEASIBLE] Streaming listener, persistent state, independent action.


def detect_energy_signals(text: str) -> list[dict[str, Any]]:
    """Detect energy/capacity indicators from input text patterns.

    [GROUNDED] Heuristic pattern matching on input text.
    Returns signal objects with type, confidence (0-1), and evidence.

    Signal types:
    - frustration: Heavy punctuation, caps, short imperatives
    - fatigue: Trailing off, incomplete thoughts, low word density
    - hyperfocus: Very long input, high technical density
    - urgency: Urgent keywords, exclamation density
    - scattered: Topic jumping, fragmented sentences
    """
    signals: list[dict[str, Any]] = []
    if not text or len(text) < 5:
        return signals

    words = text.split()
    word_count = len(words)
    char_count = len(text)

    # Frustration: heavy punctuation, caps ratio, short angry sentences
    excl_count = text.count("!")
    quest_count = text.count("?")
    caps_chars = sum(1 for c in text if c.isupper())
    caps_ratio = caps_chars / max(char_count, 1)

    if excl_count >= 3 or (caps_ratio > 0.4 and char_count > 15):
        confidence = min(1.0, (excl_count * 0.15) + (caps_ratio * 0.8))
        signals.append({
            "type": "frustration",
            "confidence": round(confidence, 2),
            "evidence": f"excl={excl_count}, caps_ratio={caps_ratio:.2f}",
        })

    # Fatigue: trailing off, low density, filler-heavy
    fatigue_markers = ["...", "..", "idk", "whatever", "nm", "nvm", "forget it", "nevermind"]
    fatigue_hits = sum(1 for m in fatigue_markers if m in text.lower())
    avg_word_len = sum(len(w) for w in words) / max(word_count, 1)

    if fatigue_hits > 0 or (avg_word_len < 3.2 and word_count > 8):
        confidence = min(1.0, fatigue_hits * 0.3 + (0.4 if avg_word_len < 3.2 else 0))
        signals.append({
            "type": "fatigue",
            "confidence": round(confidence, 2),
            "evidence": f"markers={fatigue_hits}, avg_word_len={avg_word_len:.1f}",
        })

    # Hyperfocus: very long input, high technical density
    tech_terms = re.findall(
        r"\b(?:function|class|def|import|API|schema|deploy|runtime|config|"  # noqa: E501
        r"docker|kubernetes|pipeline|endpoint|database|query|index|"  # noqa: E501
        r"error|exception|traceback|debug|log|test|assert|validate)\b",
        text, re.IGNORECASE,
    )
    tech_density = len(tech_terms) / max(word_count, 1)

    if word_count > 150 or (word_count > 80 and tech_density > 0.08):
        confidence = min(1.0, (word_count / 300) + tech_density)
        signals.append({
            "type": "hyperfocus",
            "confidence": round(confidence, 2),
            "evidence": f"words={word_count}, tech_density={tech_density:.3f}",
        })

    # Urgency: urgent keywords
    urgent_words = ["urgent", "asap", "immediately", "blocking", "production",
                    "outage", "down", "broken", "critical", "emergency"]
    urgent_hits = sum(1 for w in urgent_words if w in text.lower())
    if urgent_hits > 0:
        confidence = min(1.0, urgent_hits * 0.35)
        signals.append({
            "type": "urgency",
            "confidence": round(confidence, 2),
            "evidence": f"urgent_keywords={urgent_hits}",
        })

    # Scattered: many short sentences, topic fragmentation
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) >= 4:
        avg_sent_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_sent_len < 5:
            confidence = min(1.0, (4 - avg_sent_len) * 0.25)
            signals.append({
                "type": "scattered",
                "confidence": round(confidence, 2),
                "evidence": f"sentences={len(sentences)}, avg_len={avg_sent_len:.1f}",
            })

    return signals


def detect_drift_signals(
    input_text: str,
    active_thread: str,
    active_mode: str,
) -> dict[str, Any] | None:
    """Detect topic drift from declared thread/mode.

    [GROUNDED] Keyword overlap check. Not semantic similarity.
    Returns drift signal if detected, None otherwise.
    """
    if not active_thread:
        return None

    # Extract keywords from active thread name
    thread_words = set(re.findall(r"[a-zA-Z]{3,}", active_thread.lower()))
    input_words = set(re.findall(r"[a-zA-Z]{3,}", input_text.lower()))

    if not thread_words:
        return None

    overlap = thread_words & input_words
    overlap_ratio = len(overlap) / max(len(thread_words), 1)

    # Low overlap = possible drift
    if overlap_ratio < 0.15 and len(input_words) > 5:
        # Check if input matches a DIFFERENT mode than active
        from runtime.cognitive import MODE_SIGNALS, infer_mode
        inferred = infer_mode(input_text)
        mode_mismatch = inferred != active_mode and inferred != "execute"

        return {
            "type": "drift",
            "thread": active_thread,
            "overlap_ratio": round(overlap_ratio, 3),
            "mode_mismatch": mode_mismatch,
            "inferred_mode": inferred if mode_mismatch else None,
            "confidence": round(min(1.0, (1.0 - overlap_ratio) * 0.7
                                    + (0.3 if mode_mismatch else 0)), 2),
        }
    return None


def detect_overload_signals(input_text: str) -> dict[str, Any] | None:
    """Detect working memory overload indicators.

    [GROUNDED] Structural analysis of input text.
    Overload = too many topics, nested requests, incomplete references.
    """
    signals: list[str] = []
    words = input_text.split()
    word_count = len(words)

    # Multiple distinct requests (conjunctions + action verbs)
    action_boundaries = re.findall(
        r"\b(?:and\s+(?:also|then)?\s*(?:can|could|please|would)?|"  # noqa: E501
        r"also\s+(?:can|could|please)?|"  # noqa: E501
        r"plus\s+(?:can|could|please)?|"  # noqa: E501
        r"oh\s+and|then\s+(?:can|could|please)?)\b",
        input_text, re.IGNORECASE,
    )
    if len(action_boundaries) >= 3:
        signals.append(f"multi_request:{len(action_boundaries) + 1}")

    # Incomplete references (pronouns without clear antecedent in same sentence)
    pronoun_density = len(re.findall(
        r"\b(?:it|that|this|those|these|them)\b", input_text, re.IGNORECASE
    )) / max(word_count, 1)
    if pronoun_density > 0.08:
        signals.append(f"high_pronoun_density:{pronoun_density:.3f}")

    # Very long without structure (no punctuation, no list markers)
    if word_count > 100:
        structure_markers = len(re.findall(r"[.!?;:]|^\s*[-*]|^\s*\d+\.", input_text, re.MULTILINE))
        if structure_markers < word_count / 50:
            signals.append(f"unstructured_stream:{word_count}w/{structure_markers}markers")

    if signals:
        return {
            "type": "overload",
            "signals": signals,
            "confidence": round(min(1.0, len(signals) * 0.35), 2),
            "recommendation": "externalize" if len(signals) >= 2 else "structure",
        }
    return None


# ===========================================================================
# P2.7: SK-SCHOLAR - AuDHD Knowledge Injection Hook
# ===========================================================================

# Mode-specific cognitive patterns from PROFILE.md
_SCHOLAR_MODE_PATTERNS: dict[str, str] = {
    "execute":      "Pattern compression. Verdict first. Produce immediately. No meta-discussion.",
    "design":       "Asymmetric working memory: full system map first (architecture, invariants, interfaces, state transitions). Aggressive externalization.",
    "review":       "Meta-layer reflex: audit the system producing the outcome, not just the outcome. Surface objective function, constraints, failure modes.",
    "troubleshoot": "Monotropic lock: one hypothesis, one test, one result. Sequential elimination. No parallel investigations at low energy.",
    "osint":        "Parallel subagent decomposition. Recurse 3 degrees. Tag all data with source confidence.",
    "decide":       "Externalize tradeoffs as table. Optimize for reversibility. Cost-to-try over analysis.",
    "draft":        "Audience-matched output. Operator sets intent; system produces. No meta-commentary about the draft.",
    "rewrite":      "Source-matched register. Preserve author voice. Produce revised artifact directly.",
    "summarize":    "Maximum compression. Verdict density. No supporting detail unless explicitly requested.",
    "chat":         "Conversational. Follow operator's branch. High density per sentence. No unprompted tangents. Rabbit holes welcome when operator opens them.",
}

# Energy-specific cognitive framing
_SCHOLAR_ENERGY_FRAMING: dict[str, str] = {
    "high":   "Full cognitive capacity. All patterns active. Exploratory branches allowed.",
    "medium": "Standard capacity. Reduce exploratory branches. Prefer proven patterns.",
    "low":    "Reduced capacity. Core task only. Minimize operator cognitive load. Shortest viable path.",
    "crash":  "Emergency. Single next action. Save state. Stop. No inference overhead.",
}

# Monotropism cost table
_SCHOLAR_SWITCH_COST: dict[str, str] = {
    "0": "No switches. Monotropic beam stable.",
    "1": "One switch. Acceptable. Maintain current thread.",
    "2": "Two switches. Approaching threshold. Announce any further shifts.",
    "high": "Multiple switches. Monotropism guard active. ONE thread, ONE objective, ONE next action.",
}


def sk_scholar(ctx) -> Any:
    """SK-SCHOLAR: AuDHD knowledge-injection hook (P2.7).

    Always-on pre_execute hook. Injects PROFILE.md cognitive model
    into every skill's prompt based on current mode and energy.

    [GROUNDED] What this does:
    - Injects mode-specific cognitive patterns from PROFILE.md
    - Provides energy-appropriate cognitive constraints
    - Supplies monotropism contract enforcement
    - Frames output as augmentation (not caretaker)

    [NOT FEASIBLE] What this does NOT do:
    - Does not intercept skill-to-skill communication (no inter-skill bus)
    - Does not override orchestrator routing decisions
    - Does not maintain persistent state across requests
    - Does not act as a supervisor (orchestrator handles routing)
    """
    from runtime.hooks import HookResult
    result = HookResult()

    mode = ctx.cognitive_state.active_mode
    energy = ctx.cognitive_state.energy_level
    e_key = energy.value if hasattr(energy, "value") else str(energy)

    # Crash mode: minimal injection to avoid overhead
    if e_key == "crash":
        result.modified_prompt = (ctx.prompt or "") + (
            "\n\n## Cognitive Lens (SK-SCHOLAR: crash)\n"
            "Emergency. Single action. Save state. Stop.\n"
            "This system augments a competent adult. Crash mode reduces load, not agency.\n"
        )
        return result

    # Build cognitive lens injection
    scholar_lines = [
        f"\n\n## Cognitive Lens (SK-SCHOLAR: {mode}/{e_key})",
        "",
        "### Active Pattern",
        f"{_SCHOLAR_MODE_PATTERNS.get(mode, _SCHOLAR_MODE_PATTERNS['execute'])}",
        "",
        "### Capacity",
        f"{_SCHOLAR_ENERGY_FRAMING.get(e_key, _SCHOLAR_ENERGY_FRAMING['medium'])}",
    ]

    # Monotropism contract
    switches = ctx.cognitive_state.context_switches
    if switches >= 3:
        cost_key = "high"
    else:
        cost_key = str(switches)
    switch_msg = _SCHOLAR_SWITCH_COST.get(cost_key, _SCHOLAR_SWITCH_COST["high"])
    if switches > 0:
        scholar_lines.extend([
            "",
            "### Monotropism",
            f"{switch_msg}",
        ])

    # P2.5: Context monitoring signals (if available from prior hooks)
    energy_signals = ctx.options.get("energy_signals", [])
    if energy_signals:
        scholar_lines.extend([
            "",
            "### Detected Signals",
        ])
        for sig in energy_signals:
            if isinstance(sig, dict):
                scholar_lines.append(
                    f"- {sig.get('type', 'unknown')} "
                    f"(confidence: {sig.get('confidence', '?')}, "
                    f"evidence: {sig.get('evidence', 'none')})"
                )
            else:
                scholar_lines.append(f"- {sig}")

    # Design constraint: augmentation, not caretaker
    scholar_lines.extend([
        "",
        "### Design Constraint",
        "Cognitive augmentation for a competent adult. Not safety scaffolding.",
        "Crash mode reduces load. It does not block agency.",
        "Energy routing optimizes cost/latency. It does not restrict capability.",
        "Skills are tools the operator uses. Not interventions imposed.",
    ])

    result.modified_prompt = (ctx.prompt or "") + "\n".join(scholar_lines)

    # Store scholar metadata
    result.modified_options = {
        "scholar_mode_pattern": mode,
        "scholar_energy_frame": e_key,
        "scholar_switches": switches,
    }

    return result


# ===========================================================================
# Registry Patch
# ===========================================================================

def patch_hook_registry(
    registry: dict[str, Any],
    always_on: list[str],
) -> None:
    """Patch HOOK_REGISTRY and ALWAYS_ON_HOOKS with grounded extensions.

    Call from hooks.py:
        from runtime.hooks_scholar import patch_hook_registry
        patch_hook_registry(HOOK_REGISTRY, ALWAYS_ON_HOOKS)
    """
    registry["SK-SCHOLAR"] = sk_scholar
    if "SK-SCHOLAR" not in always_on:
        always_on.append("SK-SCHOLAR")


def get_context_monitors() -> dict[str, Any]:
    """Return context monitoring functions for integration.

    These can be called by enhanced hooks or by the orchestrator
    before hook execution to inject signals into options.

    Usage:
        monitors = get_context_monitors()
        energy_sigs = monitors['energy'](input_text)
        drift_sig = monitors['drift'](input_text, active_thread, active_mode)
        overload_sig = monitors['overload'](input_text)
    """
    return {
        "energy": detect_energy_signals,
        "drift": detect_drift_signals,
        "overload": detect_overload_signals,
    }
