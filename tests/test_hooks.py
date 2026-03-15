"""Tests for runtime.hooks module."""

import pytest
from runtime.cognitive import CognitiveState
from runtime.hooks import (
    HookContext, sk_decomp, sk_gate, sk_verify, sk_format,
    sk_prioritize, run_hooks, HOOK_REGISTRY,
)


def make_ctx(**kwargs):
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
    def test_skips_low_tier(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T2"))
        result = sk_decomp(ctx)
        assert result.decomposed_tasks is None

    def test_decomposes_list_input(self):
        ctx = make_ctx(
            cognitive_state=CognitiveState(task_tier="T4"),
            input_text="- Fix the router\n- Update the schema\n- Write tests",
        )
        result = sk_decomp(ctx)
        assert result.decomposed_tasks is not None
        assert len(result.decomposed_tasks) == 3

    def test_no_decompose_single_item(self):
        ctx = make_ctx(
            cognitive_state=CognitiveState(task_tier="T4"),
            input_text="Fix the router",
        )
        result = sk_decomp(ctx)
        assert result.decomposed_tasks is None


class TestSkGate:
    def test_adds_gate_instructions(self):
        ctx = make_ctx()
        result = sk_gate(ctx)
        assert "No em dashes" in result.modified_prompt

    def test_low_energy_adds_item_limit(self):
        ctx = make_ctx(cognitive_state=CognitiveState(energy_level="low"))
        result = sk_gate(ctx)
        assert "3 items or fewer" in result.modified_prompt

    def test_crash_adds_state_only(self):
        ctx = make_ctx(cognitive_state=CognitiveState(energy_level="crash"))
        result = sk_gate(ctx)
        assert "state summary" in result.modified_prompt

    def test_t5_requires_dual_model(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T5"))
        result = sk_gate(ctx)
        assert "dual-model" in result.modified_prompt


class TestSkVerify:
    def test_t3_adds_verification(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T3"))
        result = sk_verify(ctx)
        assert result.modified_prompt is not None
        assert "[OBS]" in result.modified_prompt

    def test_t1_no_verification(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T1"))
        result = sk_verify(ctx)
        assert result.modified_prompt is None

    def test_t5_mandatory(self):
        ctx = make_ctx(cognitive_state=CognitiveState(task_tier="T5"))
        result = sk_verify(ctx)
        assert "MANDATORY" in result.modified_prompt


class TestSkPrioritize:
    def test_no_guard_low_switches(self):
        ctx = make_ctx(cognitive_state=CognitiveState(context_switches=1))
        result = sk_prioritize(ctx)
        assert result.modified_prompt is None

    def test_guard_high_switches(self):
        ctx = make_ctx(cognitive_state=CognitiveState(context_switches=5))
        result = sk_prioritize(ctx)
        assert "Monotropism Guard" in result.modified_prompt


class TestSkFormat:
    def test_execute_template(self):
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="execute"))
        result = sk_format(ctx)
        assert "Goal, Constraints" in result.modified_prompt

    def test_decide_template(self):
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="decide"))
        result = sk_format(ctx)
        assert "Upside" in result.modified_prompt

    def test_chat_no_template(self):
        ctx = make_ctx(cognitive_state=CognitiveState(active_mode="chat"))
        result = sk_format(ctx)
        assert result.modified_prompt is None


class TestRunHooks:
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

    def test_all_hooks_callable(self):
        for name, fn in HOOK_REGISTRY.items():
            assert callable(fn), f"{name} is not callable"

    def test_empty_hooks_passthrough(self):
        ctx = make_ctx()
        result = run_hooks([], ctx)
        assert result.modified_prompt is None
        assert result.gate_passed is True
