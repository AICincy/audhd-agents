"""Skill discovery and loading from skills/ directory.

Reads skill.yaml, schema.json, prompt.md, examples.json for each skill.
Merges with _base/ shared definitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def _parse_yaml(text: str) -> dict:
    """Parse YAML with pyyaml or fallback to basic parser."""
    if yaml is not None:
        return yaml.safe_load(text) or {}
    # Minimal fallback: parse simple key: value YAML
    result: dict[str, Any] = {}
    current_key = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val:
                result[key] = val
            else:
                result[key] = {}
                current_key = key
        elif stripped.startswith("- ") and current_key:
            if not isinstance(result[current_key], list):
                result[current_key] = []
            result[current_key].append(stripped[2:].strip().strip('"'))
    return result


class SkillLoader:
    """Discovers and loads skill definitions from the skills/ directory."""

    def __init__(self, skills_dir: Path) -> None:
        self._dir = skills_dir
        self._cache: dict[str, dict[str, Any]] = {}
        self._base_prompt: str | None = None
        self._base_schema: dict | None = None

    def _load_base(self) -> None:
        """Load shared base prompt and schema (lazy, cached)."""
        if self._base_prompt is not None:
            return
        base_dir = self._dir / "_base"
        prompt_path = base_dir / "prompt_base.md"
        schema_path = base_dir / "schema_base.json"
        self._base_prompt = prompt_path.read_text() if prompt_path.exists() else ""
        self._base_schema = (
            json.loads(schema_path.read_text()) if schema_path.exists() else {}
        )

    def list_names(self) -> list[str]:
        """Return sorted list of skill directory names."""
        if not self._dir.exists():
            return []
        return sorted(
            d.name
            for d in self._dir.iterdir()
            if d.is_dir()
            and not d.name.startswith("_")
            and (d / "skill.yaml").exists()
        )

    def list_all(self) -> list[dict[str, str]]:
        """Return metadata dicts for all skills."""
        results: list[dict[str, str]] = []
        for name in self.list_names():
            skill_yaml = self._dir / name / "skill.yaml"
            meta = _parse_yaml(skill_yaml.read_text()) if skill_yaml.exists() else {}
            results.append({
                "name": meta.get("name", name),
                "display_name": meta.get("display_name", name),
                "category": meta.get("category", ""),
                "description": meta.get("description", "").strip(),
            })
        return results

    def load(self, name: str) -> dict[str, Any] | None:
        """Load a complete skill definition by name.

        Returns dict with keys: meta, schema, prompt, examples, base_prompt, base_schema.
        Returns None if skill not found.
        """
        if name in self._cache:
            return self._cache[name]

        skill_dir = self._dir / name
        if not skill_dir.is_dir():
            # Fuzzy match: partial name
            for candidate in self.list_names():
                if name in candidate or candidate.endswith(name):
                    skill_dir = self._dir / candidate
                    name = candidate
                    break
            else:
                return None

        self._load_base()

        # Read skill files
        meta = self._read_yaml(skill_dir / "skill.yaml")
        if not meta:
            return None

        schema = self._read_json(skill_dir / "schema.json") or {}
        prompt = self._read_text(skill_dir / "prompt.md") or ""
        examples = self._read_json(skill_dir / "examples.json") or []

        result = {
            "meta": meta,
            "schema": schema,
            "prompt": prompt,
            "examples": examples,
            "base_prompt": self._base_prompt,
            "base_schema": self._base_schema,
        }
        self._cache[name] = result
        return result

    def _read_yaml(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        return _parse_yaml(path.read_text())

    @staticmethod
    def _read_json(path: Path) -> Any | None:
        if not path.exists():
            return None
        return json.loads(path.read_text())

    @staticmethod
    def _read_text(path: Path) -> str | None:
        if not path.exists():
            return None
        return path.read_text()
