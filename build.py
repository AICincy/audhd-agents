#!/usr/bin/env python3
"""
AUDHD Cognitive Swarm Protocol: AIO Build System
Reads canonical skill definitions and generates LLM-specific manifests.

Usage:
  python build.py                         # Build all skills, all adapters
  python build.py --skill code-reviewer   # Build one skill
  python build.py --adapter openai        # Build all skills for one adapter
  python build.py --external-skills ../audhd-skills  # Include VoltAgent .md skills
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


def resolve_schema(schema: dict, skill_dir: Path) -> dict:
    """Resolve allOf/$ref in a skill schema to a flat schema.

    Skills using allOf+$ref (e.g. referencing _base/schema_base.json)
    produce schemas where properties/required are nested inside allOf
    sub-schemas rather than at top level. build_openai/build_gemini only
    read top-level schema["properties"] and schema["required"], so we
    must merge everything up before handing off to builders.

    Returns a new dict with merged properties/required at top level.
    """
    if "allOf" not in schema:
        return schema

    merged_properties = {}
    merged_required = []

    # Preserve top-level fields that aren't allOf
    result = {}
    for key, val in schema.items():
        if key == "allOf":
            continue
        result[key] = val

    for sub in schema["allOf"]:
        resolved_sub = sub

        # Resolve $ref to file path relative to skill directory
        if "$ref" in sub:
            ref_path = skill_dir / sub["$ref"]
            if ref_path.exists():
                with open(ref_path) as f:
                    resolved_sub = json.load(f)
            else:
                # $ref target missing; skip with warning
                print(f"  WARN: $ref target not found: {ref_path}")
                continue

        # Merge properties
        if "properties" in resolved_sub:
            merged_properties.update(resolved_sub["properties"])

        # Merge required (deduplicate, preserve order)
        if "required" in resolved_sub:
            for req in resolved_sub["required"]:
                if req not in merged_required:
                    merged_required.append(req)

        # Carry over definitions if present (e.g. from schema_base.json)
        if "definitions" in resolved_sub and "definitions" not in result:
            result["definitions"] = resolved_sub["definitions"]

        # Resolve internal $ref in merged properties (e.g. {"$ref": "#/definitions/cognitive_state"})
        if "definitions" in result:
            for prop_key, prop_val in list(merged_properties.items()):
                if isinstance(prop_val, dict) and "$ref" in prop_val:
                    ref_str = prop_val["$ref"]
                    if ref_str.startswith("#/definitions/"):
                        def_name = ref_str.split("/")[-1]
                        if def_name in result["definitions"]:
                            merged_properties[prop_key] = result["definitions"][def_name]

    result["properties"] = merged_properties
    result["required"] = merged_required

    # Ensure type is set
    if "type" not in result:
        result["type"] = "object"

    return result


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
            raw_schema = json.load(f)
        skill["schema"] = resolve_schema(raw_schema, skill_dir)
    else:
        skill["schema"] = {}

    if examples_json.exists():
        with open(examples_json) as f:
            skill["examples"] = json.load(f)
    else:
        skill["examples"] = []

    return skill


def load_voltagent_skill(skill_dir: Path) -> dict:
    """Load a VoltAgent-format skill from .md + .json files.

    F3 fix: Supports audhd-skills repo layout where each skill directory
    contains prompt_base.md and schema_base.json (with optional _base/ shared).
    """
    prompt_md = skill_dir / "prompt_base.md"
    schema_json = skill_dir / "schema_base.json"

    if not prompt_md.exists():
        raise FileNotFoundError(f"Missing prompt_base.md in {skill_dir}")

    skill_name = skill_dir.name
    prompt_text = prompt_md.read_text()

    # Extract description from first non-empty, non-heading line
    description = ""
    for line in prompt_text.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            description = stripped[:200]
            break

    skill = {
        "name": skill_name,
        "description": description,
        "prompt": prompt_text,
        "schema": {},
        "examples": [],
        "voltagent": True,
    }

    if schema_json.exists():
        with open(schema_json) as f:
            raw_schema = json.load(f)
        skill["schema"] = resolve_schema(raw_schema, skill_dir)

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


def build_skill(skill_dir: Path, adapters: list, voltagent: bool = False) -> dict:
    """Build one skill for specified adapters."""
    skill = load_voltagent_skill(skill_dir) if voltagent else load_skill(skill_dir)
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
    parser.add_argument(
        "--external-skills",
        help="Path to external VoltAgent skills directory (e.g. ../audhd-skills)",
    )
    args = parser.parse_args()

    adapters = ADAPTERS if args.adapter == "all" else [args.adapter]

    for adapter in adapters:
        (DIST_DIR / adapter).mkdir(parents=True, exist_ok=True)

    # Internal skills (skill.yaml format)
    if args.skill:
        skill_dirs = [SKILLS_DIR / args.skill]
        if not skill_dirs[0].exists():
            print(f"Error: Skill directory not found: {skill_dirs[0]}")
            sys.exit(1)
    else:
        skill_dirs = sorted([p.parent for p in SKILLS_DIR.rglob("skill.yaml")])

    if not skill_dirs and not args.external_skills:
        print("No skills found. Add skill directories under skills/")
        sys.exit(0)

    built = 0
    errors = []

    # Build internal skills
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

    # Build external VoltAgent skills (F3 fix)
    if args.external_skills:
        ext_path = Path(args.external_skills)
        if not ext_path.exists():
            print(f"Warning: External skills path not found: {ext_path}")
        else:
            ext_dirs = sorted([
                d for d in ext_path.iterdir()
                if d.is_dir()
                and not d.name.startswith("_")
                and not d.name.startswith(".")
                and (d / "prompt_base.md").exists()
            ])
            for skill_dir in ext_dirs:
                try:
                    results = build_skill(skill_dir, adapters, voltagent=True)
                    for adapter, manifest in results.items():
                        out_path = DIST_DIR / adapter / f"{skill_dir.name}.json"
                        with open(out_path, "w") as f:
                            json.dump(manifest, f, indent=2)
                    built += 1
                    print(f"  OK  {skill_dir.name} (voltagent)")
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
