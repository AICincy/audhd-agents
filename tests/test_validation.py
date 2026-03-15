"""Tests for runtime.validation module."""

import pytest
from runtime.validation import validate_output


class TestEmDashDetection:
    def test_catches_em_dash(self):
        result = validate_output("This is a test \u2014 with an em dash")
        assert not result.passed
        assert any("NO_EM_DASH" in v for v in result.violations)

    def test_catches_en_dash(self):
        result = validate_output("Range: 1\u20135")
        assert not result.passed

    def test_clean_text_passes(self):
        result = validate_output("This is clean: no dashes here.")
        assert result.passed


class TestFillerDetection:
    def test_catches_filler(self):
        result = validate_output("Great question! Let me explain.")
        assert not result.passed
        assert any("NO_FILLER" in v for v in result.violations)

    def test_catches_ai_disclosure(self):
        result = validate_output("As an AI, I cannot do that.")
        assert not result.passed


class TestMotivationDetection:
    def test_catches_encouragement(self):
        result = validate_output("You've got this! Keep going!")
        assert not result.passed
        assert any("NO_MOTIVATION" in v for v in result.violations)


class TestClaimTags:
    def test_warns_missing_tags_t3(self):
        result = validate_output("The system has 51 skills.", task_tier="T3")
        assert any("CLAIM_TAGS" in w for w in result.warnings)

    def test_no_warning_with_tags(self):
        result = validate_output("The system has 51 skills. [OBS]", task_tier="T3")
        assert not any("CLAIM_TAGS" in w for w in result.warnings)

    def test_no_warning_in_chat_mode(self):
        result = validate_output(
            "The system has 51 skills.", active_mode="chat", task_tier="T3"
        )
        assert not any("CLAIM_TAGS" in w for w in result.warnings)


class TestEnergyValidation:
    def test_low_energy_warns_long_output(self):
        long_output = "\n".join(f"Line {i}" for i in range(20))
        result = validate_output(long_output, energy_level="low")
        assert any("ENERGY_LOW" in w for w in result.warnings)

    def test_crash_mode_rejects_long_output(self):
        long_output = "\n".join(f"Line {i}" for i in range(10))
        result = validate_output(long_output, energy_level="crash")
        assert not result.passed
        assert any("ENERGY_CRASH" in v for v in result.violations)


class TestVerdictFirst:
    def test_warns_context_first(self):
        result = validate_output("Before we begin, let me explain the background.")
        assert any("VERDICT_FIRST" in w for w in result.warnings)

    def test_no_warning_verdict_first(self):
        result = validate_output("Verdict: the system is functional. Here is why.")
        assert not any("VERDICT_FIRST" in w for w in result.warnings)
