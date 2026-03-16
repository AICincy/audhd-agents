"""Tests for runtime.cognitive module."""

import pytest
from pydantic import ValidationError
from runtime.cognitive import (
    CognitiveState, infer_mode, filter_model_chain,
    build_cognitive_preamble, parse_cognitive_state,
    tier_allowed,
)


class TestCognitiveState:
    def test_defaults(self):
        state = CognitiveState()
        assert state.energy_level == "medium"
        assert state.active_mode == "execute"
        assert state.task_tier == "T3"
        assert state.is_crash() is False
        assert tier_allowed(state) is True

    def test_invalid_energy_rejected(self):
        with pytest.raises(ValidationError):
            CognitiveState(energy_level="invalid")

    def test_crash_mode(self):
        state = CognitiveState(energy_level="crash")
        assert state.is_crash() is True
        assert state.output_mode == "crash"
        assert state.max_tier_num == 1

    def test_low_energy_restricts_tier(self):
        state = CognitiveState(energy_level="low", task_tier="T4")
        assert tier_allowed(state) is False

    def test_high_energy_allows_all_tiers(self):
        state = CognitiveState(energy_level="high", task_tier="T5")
        assert tier_allowed(state) is True

    def test_invalid_tier_defaults(self):
        state = CognitiveState(task_tier="X9")
        assert state.task_tier == "T3"

    def test_invalid_mode_defaults(self):
        state = CognitiveState(active_mode="nonexistent")
        assert state.active_mode == "execute"


class TestInferMode:
    def test_error_triggers_troubleshoot(self):
        assert infer_mode("I got an error when running the script") == "troubleshoot"

    def test_write_triggers_draft(self):
        assert infer_mode("Write me a proposal") == "draft"

    def test_should_i_triggers_decide(self):
        assert infer_mode("Should I use React or Vue?") == "decide"

    def test_default_is_execute(self):
        assert infer_mode("Process the quarterly data") == "execute"

    def test_investigate_triggers_osint(self):
        assert infer_mode("Investigate this email address") == "osint"

    def test_summarize_mode(self):
        assert infer_mode("Summarize the meeting notes") == "summarize"

    def test_review_mode(self):
        assert infer_mode("Review this pull request") == "review"

    def test_design_mode(self):
        assert infer_mode("Design the new API") == "design"


class TestFilterModelChain:
    def test_high_energy_allows_all(self):
        chain = ["O-54P", "G-PRO", "O-54"]
        state = CognitiveState(energy_level="high")
        assert filter_model_chain(chain, state, {}) == chain

    def test_low_energy_filters_to_fast_models(self):
        alias_map = {
            "O-54P": "openai/gpt-5.4-pro",
            "G-PRO": "google/gemini-2.5-pro",
            "O-O4M": "openai/o4-mini",
        }
        chain = ["O-54P", "G-PRO", "O-O4M"]
        state = CognitiveState(energy_level="low")
        result = filter_model_chain(chain, state, alias_map)
        assert "O-54P" not in result
        assert "O-O4M" in result

    def test_crash_returns_empty(self):
        chain = ["O-54P", "G-PRO"]
        state = CognitiveState(energy_level="crash")
        assert filter_model_chain(chain, state, {}) == []

    def test_medium_allows_all(self):
        chain = ["G-PRO", "O-54P"]
        state = CognitiveState(energy_level="medium")
        assert filter_model_chain(chain, state, {}) == chain


class TestBuildCognitivePreamble:
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
        assert "Context switches" in preamble

    def test_tier_info_shown(self):
        state = CognitiveState(energy_level="low", task_tier="T4")
        preamble = build_cognitive_preamble(state)
        assert "Max tier" in preamble
        assert "T2" in preamble

    def test_active_thread_shown(self):
        state = CognitiveState(active_thread="skill-rewrite")
        preamble = build_cognitive_preamble(state)
        assert "skill-rewrite" in preamble


class TestParseCognitiveState:
    def test_from_flat_dict(self):
        options = {"energy_level": "low", "task_tier": "T2"}
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
