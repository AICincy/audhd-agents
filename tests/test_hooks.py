"""Tests for runtime.hooks module.

Validates sk_hooks implementations against AGENT.md and PROFILE.md contracts.
"""

import pytest

from runtime.cognitive import CognitiveState
from runtime.hooks import (
    HookContext,
    HookResult,
    sk_decomp,
    sk_bridge,
    sk_gate,
    sk_verify,
    sk_prioritize,
    sk_format,
    run_hooks,
    HOOK_REGISTRY,
)


def make_ctx(**kwargs) -> HookContext:
    """Create a HookContext with sensible defaults."""
    defaults = {
        "skill_id": "test-skill",
        "cognitive_state": CognitiveState(),
        "input_text": "Test input",
        "prompt": "Test prompt",
        "options": {},
    }
    defaults.update(kwargs)
    return HookContext(**defaults)


class TestSkDecomp:
    """SK-DECOMP: Task decomposition for T4+ tasks."""

    def test_skips_low_tier(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T2"))
        result = sk_decomp(ctx)
        assert result.decomposed_tasks is None

    def test_skips_t3(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T3"))
        result = sk_decomp(ctx)
        assert result.decomposed_tasks is None

    def test_decomposes_list_input_at_t4(self):
        ctx = make_ctx(
            cognitive_state=CognitiveState(task_tier="T4"),
            input_text="- Fix the router\n- Update the schema\n- Write tests",
        )
        result = sk_decomp(ctx)
        assert result.decomposed_tasks is not None
        assert len(result.decomposed_tasks) == 3

    def test_no_decompose_for_single_item(self):
        ctx = make_ctx(
            cognitive_state=CognitiveState(task_tier="T5"),
            input_text="Fix the router",
        )
        result = sk_decomp(ctx)
        assert result.decomposed_tasks is None


class TestSkBridge:
    """SK-BRIDGE: Handoff state bridging."""

    def test_extracts_handoff_context(self):
        ctx = make_ctx(
            input_text="HANDOFF\nFROM: C-OP46\nCONTEXT: Previous analysis found 3 issues\nARTIFACTS: report.md"
        )
        result = sk_bridge(ctx)
        assert "Previous analysis" in result.bridged_context

    def test_bridges_partial_results(self):
        ctx = make_ctx(options={"partial_results": "Step 1 completed"})
        result = sk_bridge(ctx)
        assert "Step 1 completed" in result.bridged_context

    def test_noop_without_handoff_markers(self):
        ctx = make_ctx(input_text="Just a normal request")
        result = sk_bridge(ctx)
        assert result.bridged_context == ""


class TestSkGate:
    """SK-GATE: Quality gate prompt injection."""

    def test_adds_gate_instructions(self):
        ctx = make_ctx()
        result = sk_gate(ctx)
        assert result.modified_prompt is not None
        assert "No em dashes" in result.modified_prompt

    def test_low_energy_adds_item_limit(self):
        ctx = make_ctx(cognitive_state=CognitiveState(energy_level="low"))
        result = sk_gate(ctx)
        assert "3 items or fewer" in result.modified_prompt

    def test_crash_energy_restricts_output(self):
        ctx = make_ctx(cognitive_state=CognitiveState(energy_level="crash"))
        result = sk_gate(ctx)
        assert "state summary" in result.modified_prompt

    def test_t5_requires_dual_model(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T5"))
        result = sk_gate(ctx)
        assert "dual-model" in result.modified_prompt

    def test_claim_tags_enforced(self):
        ctx = make_ctx()
        result = sk_gate(ctx)
        assert "[OBS]" in result.modified_prompt

    def test_chat_mode_skips_claim_tags(self):
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="chat"))
        result = sk_gate(ctx)
        assert "Claim tags" not in (result.modified_prompt or "")


class TestSkVerify:
    """SK-VERIFY: Tier-based verification requirements."""

    def test_t3_adds_optional_verification(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T3"))
        result = sk_verify(ctx)
        assert result.modified_prompt is not None
        assert "optional" in result.modified_prompt

    def test_t5_mandatory_dual_model(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T5"))
        result = sk_verify(ctx)
        assert "mandatory_dual_model" in result.modified_prompt
        assert "confidence score" in result.modified_prompt

    def test_t1_no_verification(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T1"))
        result = sk_verify(ctx)
        assert result.modified_prompt is None

    def test_t2_no_verification(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T2"))
        result = sk_verify(ctx)
        assert result.modified_prompt is None


class TestSkPrioritize:
    """SK-PRIORITIZE: Monotropism guard."""

    def test_activates_on_high_switches(self):
        ctx = make_ctx(cognitive_state=CognitiveState(context_switches=5))
        result = sk_prioritize(ctx)
        assert result.modified_prompt is not None
        assert "ONE result" in result.modified_prompt

    def test_inactive_at_low_switches(self):
        ctx = make_ctx(cognitive_state=CognitiveState(context_switches=1))
        result = sk_prioritize(ctx)
        assert result.modified_prompt is None


class TestSkFormat:
    """SK-FORMAT: Mode-aware output template."""

    def test_execute_mode_template(self):
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="execute"))
        result = sk_format(ctx)
        assert "Goal, Constraints" in result.modified_prompt

    def test_decide_mode_template(self):
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="decide"))
        result = sk_format(ctx)
        assert "Revert path" in result.modified_prompt

    def test_troubleshoot_mode_template(self):
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="troubleshoot"))
        result = sk_format(ctx)
        assert "Hypothesis" in result.modified_prompt

    def test_chat_mode_no_template(self):
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="chat"))
        result = sk_format(ctx)
        assert result.modified_prompt is None


class TestRunHooks:
    """Hook chain execution and merging."""

    def test_unknown_hook_warns(self):
        ctx = make_ctx()
        result = run_hooks(["SK-NONEXISTENT"], ctx)
        assert len(result.validation_warnings) > 0
        assert "Unknown hook" in result.validation_warnings[0]

    def test_chained_hooks_merge(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T4"))
        result = run_hooks(["SK-GATE", "SK-VERIFY"], ctx)
        prompt = result.modified_prompt or ""
        assert "No em dashes" in prompt
        assert "[OBS]" in prompt

    def test_empty_hook_list(self):
        ctx = make_ctx()
        result = run_hooks([], ctx)
        assert result.gate_passed is True
        assert result.modified_prompt is None

    def test_all_registered_hooks_are_callable(self):
        for name, fn in HOOK_REGISTRY.items():
            assert callable(fn), f"{name} is not callable"

    def test_hook_order_matters(self):
        # SK-FORMAT should set template, SK-GATE should add checks on top
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="decide"))
        result = run_hooks(["SK-FORMAT", "SK-GATE"], ctx)
        prompt = result.modified_prompt or ""
        # Both should be present
        assert "Revert path" in prompt
        assert "No em dashes" in prompt
