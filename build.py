#!/usr/bin/env python3
"""
AUDHD Cognitive Swarm Protocol: AIO Build System
Reads canonical skill definitions and generates LLM-specific manifests.

Usage:
  python build.py                         # Build all skills, all adapters
  python build.py --skill code-reviewer   # Build one skill
  python build.py --adapter openai        # Build all skills for one adapter
"""

import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. Run: pip install pyyaml")
    sys.exit(1)

SKILLS_DIR = Path("skills")
DIST_DIR = Path("dist")
ADAPTERS = ["openai", "gemini"]


def load_skill(skill_dir: Path) -> dict:
    """Load canonical skill files from a skill directory."""
    skill_yaml = skill_dir / "skill.yaml"
    prompt_md = skill_dir / "prompt.md"
    schema_json = skill_dir / "schema.json"
    examples_json = skill_dir / "examples.json"

    if not skill_yaml.exists():
        raise FileNotFoundError(f"Missing skill.yaml in {skill_dir}")

    with open(skill_yaml) as f:
        skill = yaml.safe_load(f)

    skill["prompt"] = prompt_md.read_text() if prompt_md.exists() else ""

    if schema_json.exists():
        with open(schema_json) as f:
            skill["schema"] = json.load(f)
    else:
        skill["schema"] = {}

    if examples_json.exists():
        with open(examples_json) as f:
            skill["examples"] = json.load(f)
    else:
        skill["examples"] = []

    return skill


def build_openai(skill: dict) -> dict:
    """Generate OpenAI function tool definition."""
    schema = skill.get("schema", {})
    return {
        "type": "function",
        "function": {
            "name": skill["name"],
            "description": skill.get("description", "").strip(),
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            },
        },
    }



def _convert_gemini_property(val: dict) -> dict:
    """Recursively convert a JSON Schema property to Gemini format."""
    prop = {
        "type": val.get("type", "STRING").upper(),
        "description": val.get("description", ""),
    }
    if "enum" in val:
        prop["enum"] = val["enum"]
    # Recurse into object properties
    if val.get("type") == "object" and "properties" in val:
        prop["properties"] = {}
        for k, v in val["properties"].items():
            prop["properties"][k] = _convert_gemini_property(v)
        if "required" in val:
            prop["required"] = val["required"]
    # Handle array items
    if val.get("type") == "array" and "items" in val:
        prop["items"] = _convert_gemini_property(val["items"])
    return prop


def build_gemini(skill: dict) -> dict:
    """Generate Gemini function declaration with recursive schema."""
    schema = skill.get("schema", {})
    properties = {}
    for key, val in schema.get("properties", {}).items():
        properties[key] = _convert_gemini_property(val)

    return {
        "name": skill["name"],
        "description": skill.get("description", "").strip(),
        "parameters": {
            "type": "OBJECT",
            "properties": properties,
            "required": schema.get("required", []),
        },
    }


BUILDERS = {
    "openai": build_openai,
    "gemini": build_gemini,
}


def build_skill(skill_dir: Path, adapters: list) -> dict:
    """Build one skill for specified adapters."""
    skill = load_skill(skill_dir)
    results = {}
    for adapter in adapters:
        builder = BUILDERS[adapter]
        results[adapter] = builder(skill)
    return results


def write_manifests(adapters: list):
    """Aggregate per-skill JSONs into manifest.json per adapter."""
    for adapter in adapters:
        adapter_dir = DIST_DIR / adapter
        if not adapter_dir.exists():
            continue
        tools = []
        for f in sorted(adapter_dir.glob("*.json")):
            if f.name == "manifest.json":
                continue
            with open(f) as fh:
                tools.append(json.load(fh))
        manifest_path = adapter_dir / "manifest.json"
        with open(manifest_path, "w") as fh:
            json.dump({"tools": tools, "count": len(tools)}, fh, indent=2)
        print(f"  Manifest: {manifest_path} ({len(tools)} tools)")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build LLM-specific skill manifests")
    parser.add_argument("--skill", help="Build a specific skill (directory name)")
    parser.add_argument(
        "--adapter",
        choices=ADAPTERS + ["all"],
        default="all",
        help="Target adapter (default: all)",
    )
    args = parser.parse_args()

    adapters = ADAPTERS if args.adapter == "all" else [args.adapter]

    for adapter in adapters:
        (DIST_DIR / adapter).mkdir(parents=True, exist_ok=True)

    if args.skill:
        skill_dirs = [SKILLS_DIR / args.skill]
        if not skill_dirs[0].exists():
            print(f"Error: Skill directory not found: {skill_dirs[0]}")
            sys.exit(1)
    else:
        skill_dirs = sorted([p.parent for p in SKILLS_DIR.rglob("skill.yaml")])

    if not skill_dirs:
        print("No skills found. Add skill directories under skills/")
        sys.exit(0)

    built = 0
    errors = []
    for skill_dir in skill_dirs:
        try:
            results = build_skill(skill_dir, adapters)
            for adapter, manifest in results.items():
                out_path = DIST_DIR / adapter / f"{skill_dir.name}.json"
                with open(out_path, "w") as f:
                    json.dump(manifest, f, indent=2)
            built += 1
            print(f"  OK  {skill_dir.name}")
        except Exception as e:
            errors.append((skill_dir.name, str(e)))
            print(f"  FAIL {skill_dir.name}: {e}")

    # Generate aggregated manifests
    print()
    write_manifests(adapters)

    print(f"\nBuilt: {built} | Errors: {len(errors)} | Adapters: {', '.join(adapters)}")
    if errors:
        print("\nFailed:")
        for name, err in errors:
            print(f"  {name}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
