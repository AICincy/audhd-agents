#!/usr/bin/env python3
"""Configuration and live connectivity diagnostics for audhd-agents."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.router import SkillRouter
from runtime.app import load_skill_index
from runtime.config import RuntimeSettings


LIVE_PROMPT = "What is 2 + 2? Reply with exactly 4."
SYSTEM_PROMPT = "Reply with exactly 4."
VALIDATION_MAX_TOKENS = {
    "default": 64,
    "google": 256,
}
DEFAULT_MODELS = {
    "openai": "gpt-5.4",
    "anthropic": "claude-opus-4-6",
    "google": "gemini-2.5-pro",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("config", "live"),
        default="config",
        help="config validates repo/runtime structure only; live also makes real provider calls",
    )
    return parser.parse_args()


def classify_live_validation_error(exc) -> str:
    """Turn provider SDK errors into concrete operator guidance."""
    text = str(exc)
    lowered = text.lower()

    if "invalid x-api-key" in lowered or "authentication_error" in lowered:
        return (
            "Credential rejected by provider. Replace the API key in .env and rerun. "
            "For Anthropic, verify this is a standard API key, not an admin or console credential."
        )
    if "api key not valid" in lowered or "invalid api key" in lowered:
        return "Credential rejected by provider. Replace the configured API key and rerun."
    if "permission_denied" in lowered or "403" in lowered:
        return "Credential is present but lacks permission for the selected model or endpoint."
    if "not_found_error" in lowered or ("model:" in lowered and "was not found" in lowered):
        return "Configured model ID is not available to this account or is spelled incorrectly."
    if "rate limit" in lowered or "429" in lowered:
        return "Provider rate-limited the request. Retry after cooldown or switch models."
    return text


def print_header(title: str) -> None:
    """Print a section header."""
    print()
    print(title)
    print("-" * 50)


def check_env_surface(mode: str) -> None:
    """Report whether a repo-local .env file exists."""
    env_path = Path(".env")
    if env_path.exists():
        print("[OK]  .env file found")
        return

    if mode == "live":
        print("[WARN] .env file not found. Continuing with current shell environment.")
    else:
        print("[INFO] .env file not found. Config mode does not require local secrets.")


def load_router() -> SkillRouter:
    """Create the skill router."""
    return SkillRouter()


def print_provider_status(router: SkillRouter, mode: str) -> tuple[dict, bool]:
    """Print provider configuration status and return whether required live surfaces exist."""
    status = router.get_status()
    live_config_ok = True

    print_header("Provider Configuration")
    for provider, info in status.items():
        connected = info["connected"]
        if mode == "live":
            icon = "OK" if connected else "FAIL"
        else:
            icon = "OK" if connected else "WARN"

        key_info = f"key: {info['key_prefix']}" if info.get("key_prefix") else "no key"
        models = ", ".join(info.get("models", [])) or "none"
        print(f"  [{icon:4s}] {provider:12s} | {key_info:24s} | models: {models}")

        details = []
        if info.get("backend"):
            details.append(f"backend={info['backend']}")
        if info.get("auth_mode"):
            details.append(f"auth={info['auth_mode']}")
        if info.get("project"):
            details.append(f"project={info['project']}")
        if info.get("location"):
            details.append(f"location={info['location']}")
        if details:
            print(f"         -> {', '.join(details)}")

        if info.get("error"):
            print(f"         -> {info['error']}")

        if mode == "live" and not connected:
            live_config_ok = False

    return status, live_config_ok


def validate_aliases(router: SkillRouter) -> bool:
    """Ensure every alias resolves to a configured provider/model tuple."""
    print_header("Alias Resolution")
    alias_ok = True
    provider_names = set(router.config.get("providers", {}).keys())

    for alias, target in router.alias_map.items():
        provider, model = router.resolve_alias(alias)
        resolvable = bool(provider and model and provider in provider_names)
        icon = "OK" if resolvable else "FAIL"
        print(
            f"  [{icon:4s}] {alias:8s} -> {target:32s} "
            f"{'(resolvable)' if resolvable else '(invalid alias target)'}"
        )
        if not resolvable:
            alias_ok = False

    return alias_ok


def validate_instruction_stack() -> bool:
    """Ensure all required markdown instruction files exist."""
    print_header("Instruction Stack Check")
    all_found = True
    required_files = [
        Path("PROFILE.md"),
        Path("SKILL.md"),
        Path("TOOL.md"),
        Path("models/OPENAI.md"),
        Path("models/ANTHROPIC.md"),
        Path("models/GEMINI.md"),
    ]

    for file_path in required_files:
        exists = file_path.exists()
        icon = "OK" if exists else "FAIL"
        print(f"  [{icon:4s}] {str(file_path):24s} | status: {'found' if exists else 'missing'}")
        if not exists:
            all_found = False
    return all_found


def validate_skill_loading(router: SkillRouter) -> tuple[bool, int]:
    """Ensure every canonical skill can be loaded."""
    print_header("Skill Inventory")
    try:
        categories: dict[str, list[str]] = {}
        for skill_id, path in router.skill_map.items():
            rel_parts = path.relative_to("skills").parts
            category = rel_parts[0] if len(rel_parts) > 1 else "general"
            categories.setdefault(category, []).append(skill_id)

        for cat in sorted(categories.keys()):
            skills = sorted(categories[cat])
            print(f"  {cat:12s} | {', '.join(skills)}")

        count = len(router.skill_map)
        print(f"\n  [OK  ] Loaded {count} canonical skills")
        return True, count
    except Exception as exc:
        print(f"  [FAIL] Skill preload failed: {exc}")
        return False, 0


async def validate_provider_live(router: SkillRouter, provider_name: str) -> bool:
    """Run a minimal real request against a configured provider adapter."""
    adapter = router.adapters[provider_name]
    model = next(
        iter(adapter.config.get("models", {})),
        DEFAULT_MODELS.get(provider_name, "unknown-model"),
    )
    max_tokens = VALIDATION_MAX_TOKENS.get(
        provider_name,
        VALIDATION_MAX_TOKENS["default"],
    )

    try:
        result = await adapter.execute(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=LIVE_PROMPT,
            max_tokens=max_tokens,
            temperature=0.0,
        )
        content = (result.get("content") or "").strip()
        preview = content if len(content) <= 40 else content[:37] + "..."
        print(f"  [OK  ] {provider_name:12s} | model: {model:24s} | reply: {preview!r}")
        return True
    except Exception as exc:
        detail = classify_live_validation_error(exc)
        print(f"  [FAIL] {provider_name:12s} | model: {model:24s} | {detail}")
        return False


def main() -> int:
    args = parse_args()
    settings = RuntimeSettings.from_env()

    print("=" * 60)
    print("AUDHD-AGENTS CONFIGURATION CHECK")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Required providers: {', '.join(settings.required_providers)}")
    print()

    check_env_surface(args.mode)

    try:
        router = load_router()
        print("[OK]  Router initialized")
    except Exception as exc:
        print(f"[FAIL] Router init failed: {exc}")
        print("=" * 60)
        return 1

    _, live_config_ok = print_provider_status(router, args.mode)
    stack_ok = validate_instruction_stack()
    alias_ok = validate_aliases(router)
    skills_ok, _ = validate_skill_loading(router)

    live_results = {}
    if args.mode == "live":
        for provider_name in settings.required_providers:
            print_header(f"{provider_name.capitalize()} Live Validation")
            if provider_name not in router.adapters:
                print(f"  [FAIL] {provider_name:12s} | adapter not initialized")
                live_results[provider_name] = False
                continue
            live_results[provider_name] = asyncio.run(
                validate_provider_live(router, provider_name)
            )

    print()
    print("=" * 60)
    if args.mode == "config":
        config_ok = stack_ok and alias_ok and skills_ok
        if config_ok:
            print("CONFIG VALIDATION PASSED.")
            print("Repo structure, alias routing, and skill loading are consistent.")
        else:
            print("CONFIG VALIDATION FAILED. Fix alias or skill-loading errors above.")
        print("=" * 60)
        return 0 if config_ok else 1

    live_ok = live_config_ok and stack_ok and alias_ok and skills_ok and all(
        live_results.get(provider, False) for provider in settings.required_providers
    )
    if live_ok:
        print("WORKSPACE LIVE VALIDATION PASSED.")
        print("All required providers passed configuration and live-request checks.")
    else:
        if not live_config_ok:
            print("SOME REQUIRED PROVIDERS ARE NOT CONFIGURED.")
        if not stack_ok:
            print("INSTRUCTION STACK FILES MISSING.")
        if not alias_ok:
            print("ALIAS ROUTING FAILED.")
        if not skills_ok:
            print("SKILL PRELOAD FAILED.")
        for provider, passed in live_results.items():
            if not passed:
                print(f"{provider.upper()} LIVE VALIDATION FAILED.")
    print("=" * 60)
    return 0 if live_ok else 1


if __name__ == "__main__":
    sys.exit(main())
