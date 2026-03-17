"""Tests for engineering-github-pr-lister skill structure and schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

SKILL_DIR = Path(__file__).parent.parent / "skills" / "engineering-github-pr-lister"
BASE_SCHEMA = Path(__file__).parent.parent / "skills" / "_base" / "schema_base.json"


class TestSkillFiles:
    """All four required skill files must exist and be non-empty."""

    def test_skill_yaml_exists(self):
        assert (SKILL_DIR / "skill.yaml").exists()

    def test_prompt_md_exists(self):
        assert (SKILL_DIR / "prompt.md").exists()

    def test_schema_json_exists(self):
        assert (SKILL_DIR / "schema.json").exists()

    def test_examples_json_exists(self):
        assert (SKILL_DIR / "examples.json").exists()


class TestSkillYaml:
    """skill.yaml must follow the canonical skill contract."""

    @pytest.fixture(scope="class")
    def skill(self):
        with open(SKILL_DIR / "skill.yaml") as f:
            return yaml.safe_load(f)

    def test_name_matches_directory(self, skill):
        assert skill["name"] == "engineering-github-pr-lister"

    def test_has_display_name(self, skill):
        assert skill.get("display_name"), "display_name must be non-empty"

    def test_capability_is_research(self, skill):
        assert "research" in skill["capabilities"]

    def test_primary_model_set(self, skill):
        assert skill["models"]["primary"]

    def test_fallback_chain_is_list(self, skill):
        assert isinstance(skill["models"]["fallback"], list)
        assert len(skill["models"]["fallback"]) >= 1

    def test_input_text_required(self, skill):
        required_inputs = [i["name"] for i in skill["inputs"] if i.get("required")]
        assert "input_text" in required_inputs

    def test_has_outputs(self, skill):
        assert skill.get("outputs"), "outputs list must be non-empty"

    def test_pull_requests_in_outputs(self, skill):
        output_names = [o["name"] for o in skill["outputs"]]
        assert "pull_requests" in output_names


class TestSchemaJson:
    """schema.json must extend the base schema via allOf."""

    @pytest.fixture(scope="class")
    def schema(self):
        with open(SKILL_DIR / "schema.json") as f:
            return json.load(f)

    def test_uses_allof(self, schema):
        assert "allOf" in schema, "schema must extend base via allOf"

    def test_base_ref_present(self, schema):
        refs = [s.get("$ref", "") for s in schema["allOf"]]
        assert any("schema_base.json" in r for r in refs)

    def test_input_text_in_properties(self, schema):
        skill_props = next(
            s for s in schema["allOf"] if "properties" in s
        )
        assert "input_text" in skill_props["properties"]

    def test_input_text_required(self, schema):
        skill_layer = next(s for s in schema["allOf"] if "properties" in s)
        assert "input_text" in skill_layer.get("required", [])

    def test_optional_fields_present(self, schema):
        skill_props = next(s for s in schema["allOf"] if "properties" in s)
        props = skill_props["properties"]
        assert "author" in props
        assert "label" in props
        assert "limit" in props

    def test_limit_has_enum(self, schema):
        skill_props = next(s for s in schema["allOf"] if "properties" in s)
        limit = skill_props["properties"]["limit"]
        assert "enum" in limit
        assert "10" in limit["enum"]


class TestExamplesJson:
    """examples.json must be a non-empty list of valid example objects."""

    @pytest.fixture(scope="class")
    def examples(self):
        with open(SKILL_DIR / "examples.json") as f:
            return json.load(f)

    def test_is_list(self, examples):
        assert isinstance(examples, list)

    def test_has_at_least_one_example(self, examples):
        assert len(examples) >= 1

    def test_each_example_has_description(self, examples):
        for ex in examples:
            assert ex.get("description"), "every example must have a description"

    def test_each_example_has_input(self, examples):
        for ex in examples:
            assert "input" in ex

    def test_each_example_has_input_text(self, examples):
        for ex in examples:
            assert ex["input"].get("input_text"), "every example input must have input_text"

    def test_each_example_has_cognitive_state(self, examples):
        for ex in examples:
            assert "cognitive_state" in ex["input"]

    def test_cognitive_state_has_energy_level(self, examples):
        for ex in examples:
            cs = ex["input"]["cognitive_state"]
            assert cs.get("energy_level") in {"high", "medium", "low", "crash"}


class TestPromptMd:
    """prompt.md must contain all required structural sections."""

    @pytest.fixture(scope="class")
    def prompt(self):
        return (SKILL_DIR / "prompt.md").read_text()

    def test_has_goal_section(self, prompt):
        assert "## Goal" in prompt

    def test_has_energy_levels(self, prompt):
        for level in ("HIGH", "MEDIUM", "LOW", "CRASH"):
            assert f"### {level}" in prompt

    def test_has_output_structure(self, prompt):
        assert "## Output Structure" in prompt

    def test_has_pull_requests_in_output(self, prompt):
        assert "pull_requests" in prompt

    def test_has_claim_tags_section(self, prompt):
        assert "## Claim Tags" in prompt

    def test_has_monotropism_guard(self, prompt):
        assert "Monotropism" in prompt

    def test_crash_defers_work(self, prompt):
        # CRASH section must indicate deferral, not active work
        crash_start = prompt.index("### CRASH")
        crash_block = prompt[crash_start: crash_start + 200]
        assert any(
            word in crash_block.lower()
            for word in ("defer", "retry", "empty", "no new")
        ), "CRASH section must explicitly defer work"
