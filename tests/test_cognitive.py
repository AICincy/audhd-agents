"""Tests for runtime.cognitive module.

Validates cognitive state parsing, mode inference, model filtering,
and preamble generation against PROFILE.md and AGENT.md contracts.
"""

import pytest

from runtime.cognitive import (
    CognitiveState,
    infer_mode,
    filter_model_chain,
    build_cognitive_preamble,
    parse_cognitive_state,
    ENERGY_ROUTING,
    TIER_ORDER,
)


class TestCognitiveState:
    """CognitiveState dataclass validation."""

    def test_defaults(self):
        state = CognitiveState()
        assert state.energy_level == "medium"
        assert state.active_mode == "execute"
        assert state.task_tier == "T3"
        assert state.is_crash is False
        assert state.tier_allowed is True

    def test_invalid_energy_defaults_to_medium(self):
        state = CognitiveState(energy_level="invalid")
        assert state.energy_level == "medium"

    def test_invalid_tier_defaults_to_t3(self):
        state = CognitiveState(task_tier="TX")
        assert state.task_tier == "T3"

    def test_invalid_mode_defaults_to_execute(self):
        state = CognitiveState(active_mode="invalid")
        assert state.active_mode == "execute"

    def test_crash_mode(self):
        state = CognitiveState(energy_level="crash")
        assert state.is_crash is True
        assert state.output_mode == "crash"
        assert state.max_tier_num == 1

    def test_low_energy_restricts_tier(self):
        state = CognitiveState(energy_level="low", task_tier="T4")
        assert state.tier_allowed is False

    def test_low_energy_allows_t2(self):
        state = CognitiveState(energy_level="low", task_tier="T2")
        assert state.tier_allowed is True

    def test_high_energy_allows_all_tiers(self):
        state = CognitiveState(energy_level="high", task_tier="T5")
        assert state.tier_allowed is True

    def test_medium_energy_blocks_t5(self):
        state = CognitiveState(energy_level="medium", task_tier="T5")
        assert state.tier_allowed is False

    def test_routing_property(self):
        state = CognitiveState(energy_level="high")
        assert state.routing["max_tier"] == "T5"
        assert state.routing["model_pool"] == "all"


class TestInferMode:
    """PROFILE.md mode routing from natural language."""

    def test_error_triggers_troubleshoot(self):
        assert infer_mode("I got an error when running the script") == "troubleshoot"

    def test_crash_triggers_troubleshoot(self):
        assert infer_mode("The server crashed") == "troubleshoot"

    def test_write_triggers_draft(self):
        assert infer_mode("Write me a proposal") == "draft"

    def test_compose_triggers_draft(self):
        assert infer_mode("Compose an email") == "draft"

    def test_should_i_triggers_decide(self):
        assert infer_mode("Should I use React or Vue?") == "decide"

    def test_compare_triggers_decide(self):
        assert infer_mode("Compare these two options") == "decide"

    def test_investigate_triggers_osint(self):
        assert infer_mode("Investigate this email address") == "osint"

    def test_summarize_triggers_summarize(self):
        assert infer_mode("Give me a tldr of this report") == "summarize"

    def test_review_triggers_review(self):
        assert infer_mode("Review this code") == "review"

    def test_build_triggers_design(self):
        assert infer_mode("Build a new API") == "design"

    def test_default_is_execute(self):
        assert infer_mode("Process the quarterly data") == "execute"

    def test_empty_input_is_execute(self):
        assert infer_mode("") == "execute"


class TestFilterModelChain:
    """AGENT.md energy-adaptive model filtering."""

    def test_high_energy_allows_all(self):
        chain = ["C-OP46", "G-PRO", "O-54"]
        state = CognitiveState(energy_level="high")
        assert filter_model_chain(chain, state, {}) == chain

    def test_medium_energy_allows_all(self):
        chain = ["C-OP46", "G-PRO"]
        state = CognitiveState(energy_level="medium")
        assert filter_model_chain(chain, state, {}) == chain

    def test_low_energy_filters_to_fast_models(self):
        chain = ["C-OP46", "G-PRO", "C-SN46"]
        state = CognitiveState(energy_level="low")
        result = filter_model_chain(chain, state, {})
        assert "C-OP46" not in result
        assert "G-PRO" in result
        assert "C-SN46" in result

    def test_crash_returns_empty(self):
        chain = ["C-OP46", "G-PRO"]
        state = CognitiveState(energy_level="crash")
        assert filter_model_chain(chain, state, {}) == []

    def test_empty_chain_returns_empty(self):
        state = CognitiveState(energy_level="high")
        assert filter_model_chain([], state, {}) == []


class TestBuildCognitivePreamble:
    """Runtime cognitive preamble generation."""

    def test_contains_energy_level(self):
        state = CognitiveState(energy_level="low")
        preamble = build_cognitive_preamble(state)
        assert "low" in preamble

    def test_crash_mode_warning(self):
        state = CognitiveState(energy_level="crash")
        preamble = build_cognitive_preamble(state)
        assert "CRASH MODE ACTIVE" in preamble

    def test_context_switch_warning(self):
        state = CognitiveState(context_switches=5)
        preamble = build_cognitive_preamble(state)
        assert "context switches" in preamble

    def test_tier_blocked_warning(self):
        state = CognitiveState(energy_level="low", task_tier="T4")
        preamble = build_cognitive_preamble(state)
        assert "TIER BLOCKED" in preamble

    def test_active_thread_shown(self):
        state = CognitiveState(active_thread="audit-v4")
        preamble = build_cognitive_preamble(state)
        assert "audit-v4" in preamble

    def test_no_extra_warnings_at_defaults(self):
        state = CognitiveState()
        preamble = build_cognitive_preamble(state)
        assert "WARNING" not in preamble
        assert "BLOCKED" not in preamble
        assert "CRASH" not in preamble


class TestParseCognitiveState:
    """Cognitive state extraction from request options."""

    def test_from_nested_object(self):
        options = {"cognitive_state": {"energy_level": "low", "task_tier": "T2"}}
        state = parse_cognitive_state(options)
        assert state.energy_level == "low"
        assert state.task_tier == "T2"

    def test_from_flat_options(self):
        options = {"energy_level": "high"}
        state = parse_cognitive_state(options)
        assert state.energy_level == "high"

    def test_empty_options_returns_defaults(self):
        state = parse_cognitive_state({})
        assert state.energy_level == "medium"
        assert state.task_tier == "T3"

    def test_nested_takes_priority(self):
        options = {
            "energy_level": "high",
            "cognitive_state": {"energy_level": "low"},
        }
        state = parse_cognitive_state(options)
        assert state.energy_level == "low"
