#!/usr/bin/env python3
"""sk — AuDHD Skill CLI.

Converts LLM skill definitions into executable CLI tools.

Usage:
    sk <skill-name> "input text" [options]
    sk --list
    echo "input" | sk <skill-name>
    sk <skill-name> -f input.txt --energy low --tier T2

Examples:
    sk engineering-code-reviewer "Review this PR diff" --focus security
    sk engineering-ai-engineer "Build a rec system" --stage design --infra GCP
    sk engineering-git-workflow-master "Branching strategy for monorepo" --team-size small-2-5
    sk --list
    cat diff.txt | sk engineering-code-reviewer --format critical-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cli.skill_loader import SkillLoader
from cli.llm_client import call_llm
from cli.validator import validate_input


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sk",
        description="AuDHD Skill CLI: execute LLM skills from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  sk engineering-code-reviewer "Review this PR" --focus security\n'
            '  sk engineering-ai-engineer "Build a rec system" --stage design\n'
            "  sk --list\n"
            '  cat diff.txt | sk engineering-code-reviewer --format critical-only\n'
        ),
    )
    parser.add_argument("skill", nargs="?", help="Skill name (e.g. engineering-ai-engineer)")
    parser.add_argument("input_text", nargs="?", help="Primary input text")

    # Global options
    parser.add_argument("--list", action="store_true", help="List all available skills")
    parser.add_argument(
        "--energy",
        choices=["high", "medium", "low", "crash"],
        default="medium",
        help="Cognitive energy level (default: medium)",
    )
    parser.add_argument("--mode", help="Override mode routing (e.g. review, design, execute)")
    parser.add_argument(
        "--tier",
        choices=["T1", "T2", "T3", "T4", "T5"],
        default="T3",
        help="Task complexity tier (default: T3)",
    )
    parser.add_argument("--model", help="Override model alias (e.g. G-PRO, O-54P)")
    parser.add_argument("--dry-run", action="store_true", help="Show prompt without calling LLM")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output raw JSON")
    parser.add_argument("-f", "--file", help="Read input_text from file")
    parser.add_argument("--skills-dir", default=None, help="Override skills/ directory path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Skill-specific optional args (pass-through)
    parser.add_argument("--stage", help="Project stage (skill-specific)")
    parser.add_argument("--infra", help="Infrastructure constraints (skill-specific)")
    parser.add_argument("--focus", help="Review focus area (skill-specific)")
    parser.add_argument("--format", dest="output_format", help="Output detail level")
    parser.add_argument("--context", help="Additional context (skill-specific)")
    parser.add_argument("--team-size", help="Team size (skill-specific)")

    args = parser.parse_args()

    # Resolve skills directory
    if args.skills_dir:
        skills_dir = Path(args.skills_dir)
    else:
        skills_dir = Path(__file__).resolve().parent.parent / "skills"

    loader = SkillLoader(skills_dir)

    # --list: print catalog and exit
    if args.list:
        _list_skills(loader)
        return

    if not args.skill:
        parser.print_help()
        sys.exit(1)

    # Load skill definition
    skill = loader.load(args.skill)
    if not skill:
        print(f"Error: skill '{args.skill}' not found.", file=sys.stderr)
        available = loader.list_names()
        if available:
            print(f"Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    # Resolve input_text: positional arg > --file > stdin
    input_text = args.input_text
    if not input_text and args.file:
        input_text = Path(args.file).read_text().strip()
    if not input_text and not sys.stdin.isatty():
        input_text = sys.stdin.read().strip()
    if not input_text:
        print("Error: input_text required (positional arg, --file, or stdin)", file=sys.stderr)
        sys.exit(1)

    # Build cognitive state
    cognitive_state: dict = {
        "energy_level": args.energy,
        "task_tier": args.tier,
    }
    if args.mode:
        cognitive_state["active_mode"] = args.mode

    # Build payload
    payload: dict = {"input_text": input_text, "cognitive_state": cognitive_state}
    extras = {
        "stage": args.stage,
        "infra": args.infra,
        "focus": args.focus,
        "format": args.output_format,
        "context": args.context,
        "team_size": args.team_size,
    }
    for key, val in extras.items():
        if val is not None:
            payload[key] = val

    # Validate input against skill schema
    errors = validate_input(payload, skill["schema"])
    if errors:
        print("Validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    # Build system prompt: base preamble + skill prompt
    system_prompt = skill["base_prompt"] + "\n\n" + skill["prompt"]

    # Build user message with cognitive header + optional examples
    cog_header = (
        f"[Energy: {args.energy} | Tier: {args.tier}"
        f"{' | Mode: ' + args.mode if args.mode else ''}"
        f" | Skill: {skill['meta']['display_name']}]"
    )
    user_msg = cog_header + "\n\n"
    if skill.get("examples"):
        user_msg += "## Reference examples\n```json\n"
        user_msg += json.dumps(skill["examples"], indent=2)
        user_msg += "\n```\n\n"
    user_msg += "## Task\n" + input_text

    # Add skill-specific context to user message
    extra_lines = []
    for key, val in extras.items():
        if val is not None:
            extra_lines.append(f"- **{key}**: {val}")
    if extra_lines:
        user_msg += "\n\n## Parameters\n" + "\n".join(extra_lines)

    # Resolve model
    model_alias = args.model or skill["meta"]["models"]["primary"]

    # --dry-run: print prompt and exit
    if args.dry_run:
        print("=== SYSTEM PROMPT ===")
        print(system_prompt)
        print("\n=== USER MESSAGE ===")
        print(user_msg)
        print(f"\n=== MODEL: {model_alias} ===")
        if args.verbose:
            print("\n=== PAYLOAD ===")
            print(json.dumps(payload, indent=2))
        return

    if args.verbose:
        print(f"[sk] skill={args.skill} model={model_alias} energy={args.energy}", file=sys.stderr)

    # Call LLM
    response = call_llm(model_alias, system_prompt, user_msg)

    if args.json_out:
        print(json.dumps({
            "skill": args.skill,
            "model": model_alias,
            "energy": args.energy,
            "tier": args.tier,
            "response": response,
        }))
    else:
        print(response)


def _list_skills(loader: SkillLoader) -> None:
    """Print skill catalog as aligned table."""
    skills = loader.list_all()
    if not skills:
        print("No skills found.")
        return

    name_w = max(len(s["name"]) for s in skills) + 2
    cat_w = max(len(s.get("category", "")) for s in skills) + 2
    print(f"{'SKILL':<{name_w}} {'CATEGORY':<{cat_w}} DESCRIPTION")
    print(f"{'\u2500' * name_w} {'\u2500' * cat_w} {'\u2500' * 50}")
    for s in sorted(skills, key=lambda x: x["name"]):
        desc = s.get("description", "")[:50]
        print(f"{s['name']:<{name_w}} {s.get('category', ''):<{cat_w}} {desc}")


if __name__ == "__main__":
    main()
