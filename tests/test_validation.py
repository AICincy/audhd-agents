"""Tests for runtime.validation module.

Validates PROFILE.md constraint enforcement on model output.
"""

import pytest

from runtime.validation import validate_output, ValidationResult


class TestEmDashDetection:
    """PROFILE.md: No em dashes. Never."""

    def test_catches_em_dash(self):
        result = validate_output("This is a test \u2014 with an em dash")
        assert not result.passed
        assert any("NO_EM_DASH" in v for v in result.violations)

    def test_catches_en_dash(self):
        result = validate_output("Range: 1\u20135")
        assert not result.passed
        assert any("NO_EM_DASH" in v for v in result.violations)

    def test_clean_text_passes(self):
        result = validate_output("This is clean: no dashes here.")
        assert result.passed

    def test_hyphen_is_allowed(self):
        result = validate_output("This is a hyphen-separated word.")
        assert result.passed


class TestFillerDetection:
    """PROFILE.md anti-pattern: No filler."""

    def test_catches_great_question(self):
        result = validate_output("Great question! Let me explain.")
        assert not result.passed
        assert any("NO_FILLER" in v for v in result.violations)

    def test_catches_ai_disclosure(self):
        result = validate_output("As an AI, I cannot do that.")
        assert not result.passed

    def test_catches_happy_to_help(self):
        result = validate_output("I'd be happy to help with that.")
        assert not result.passed

    def test_technical_text_passes(self):
        result = validate_output(
            "The router processes requests through the model chain. [OBS]"
        )
        assert result.passed


class TestMotivationDetection:
    """PROFILE.md anti-pattern: No unsolicited encouragement."""

    def test_catches_encouragement(self):
        result = validate_output("You've got this! Keep going!")
        assert not result.passed
        assert any("NO_MOTIVATION" in v for v in result.violations)

    def test_catches_great_job(self):
        result = validate_output("Great job on the implementation!")
        assert not result.passed


class TestClaimTags:
    """PROFILE.md honesty protocol: Claim tags in structured output."""

    def test_warns_missing_tags_t3(self):
        result = validate_output(
            "The system has 51 skills.", task_tier="T3"
        )
        assert any("CLAIM_TAGS" in w for w in result.warnings)

    def test_no_warning_with_obs_tag(self):
        result = validate_output(
            "The system has 51 skills. [OBS]", task_tier="T3"
        )
        assert not any("CLAIM_TAGS" in w for w in result.warnings)

    def test_no_warning_with_drv_tag(self):
        result = validate_output(
            "The system likely has drift. [DRV]", task_tier="T3"
        )
        assert not any("CLAIM_TAGS" in w for w in result.warnings)

    def test_no_warning_in_chat_mode(self):
        result = validate_output(
            "The system has 51 skills.",
            active_mode="chat",
            task_tier="T3",
        )
        assert not any("CLAIM_TAGS" in w for w in result.warnings)

    def test_no_warning_at_t1(self):
        result = validate_output(
            "The system has 51 skills.", task_tier="T1"
        )
        assert not any("CLAIM_TAGS" in w for w in result.warnings)


class TestEnergyValidation:
    """AGENT.md energy-adaptive output compliance."""

    def test_low_energy_warns_long_output(self):
        long_output = "\n".join(f"Line {i}: some content here [OBS]" for i in range(20))
        result = validate_output(long_output, energy_level="low")
        assert any("ENERGY_LOW" in w for w in result.warnings)

    def test_low_energy_ok_for_short_output(self):
        short = "Verdict: feasible. [OBS]\nNext: deploy. [DRV]"
        result = validate_output(short, energy_level="low")
        assert not any("ENERGY_LOW" in w for w in result.warnings)

    def test_crash_mode_rejects_long_output(self):
        long_output = "\n".join(f"Line {i}" for i in range(10))
        result = validate_output(long_output, energy_level="crash")
        assert not result.passed
        assert any("ENERGY_CRASH" in v for v in result.violations)

    def test_crash_mode_ok_for_short(self):
        short = "Everything is saved. Come back when ready. [OBS]"
        result = validate_output(short, energy_level="crash")
        assert not any("ENERGY_CRASH" in v for v in result.violations)


class TestVerdictFirst:
    """PROFILE.md pattern compression: Verdict first."""

    def test_warns_context_first(self):
        result = validate_output(
            "Before we begin, let me explain the background. "
            "This is important context. Then the verdict."
        )
        assert any("VERDICT_FIRST" in w for w in result.warnings)

    def test_no_warning_for_direct_verdict(self):
        result = validate_output(
            "Verdict: The plan is feasible. [DRV]\n"
            "Supporting evidence follows."
        )
        assert not any("VERDICT_FIRST" in w for w in result.warnings)


class TestEdgeCases:
    """Edge cases and robustness."""

    def test_empty_output_warns(self):
        result = validate_output("")
        assert any("EMPTY" in w for w in result.warnings)

    def test_none_like_output(self):
        result = validate_output("   ")
        assert any("EMPTY" in w for w in result.warnings)

    def test_valid_output_passes_all(self):
        good = (
            "Verdict: All 51 skills need rewriting. [OBS]\n"
            "Evidence: Schema files contain only input_text. [OBS]\n"
            "Impact: Cognitive architecture is dead code. [DRV]\n"
            "Next: Create shared base schema. [DRV]"
        )
        result = validate_output(good, task_tier="T4")
        assert result.passed
        assert not result.violations
