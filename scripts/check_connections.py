#!/usr/bin/env python3
"""Configuration diagnostics for audhd-agents.

Run from repo root:
    python scripts/check_connections.py

Checks:
  1. .env file exists and is loaded
  2. All 3 provider auth surfaces are present
  3. Adapter initialization succeeds
  4. Model routing resolves all 11 aliases
  5. OpenAI live-request validation succeeds
  6. Anthropic live-request validation succeeds

OpenAI and Anthropic are validated with real API requests.
Google remains a configuration/routing check only.
"""

import asyncio
import sys
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def classify_live_validation_error(exc) -> str:
    """Turn provider SDK errors into concrete operator guidance."""
    text = str(exc)
    lowered = text.lower()

    if "invalid x-api-key" in lowered or "authentication_error" in lowered:
        return (
            "Credential rejected by provider. Replace the API key in .env and rerun. "
            "For Anthropic, verify this is a standard API key, not an admin or console credential."
        )
    if "not_found_error" in lowered or "model:" in lowered and "was not found" in lowered:
        return "Configured model ID is not available to this account or is spelled incorrectly."
    if "rate limit" in lowered or "429" in lowered:
        return "Provider rate-limited the request. Retry after cooldown or switch models."
    return text


def main():
    print("=" * 60)
    print("AUDHD-AGENTS CONFIGURATION CHECK")
    print("=" * 60)
    print()

    # 1. Check .env exists
    env_path = Path(".env")
    if env_path.exists():
        print("[OK]  .env file found")
    else:
        print("[FAIL] .env file not found. Run: cp .env.example .env")
        print("       Then fill in your API keys.")
        sys.exit(1)

    # 2. Initialize router (loads dotenv + config)
    try:
        from adapters.router import SkillRouter
        router = SkillRouter()
        print("[OK]  Router initialized")
    except Exception as e:
        print(f"[FAIL] Router init failed: {e}")
        sys.exit(1)

    # 3. Check adapter configuration status
    print()
    print("Provider Configuration:")
    print("-" * 50)
    status = router.get_status()
    all_ok = True
    for provider, info in status.items():
        connected = info["connected"]
        icon = "OK" if connected else "FAIL"
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
        if not connected:
            all_ok = False

    # 4. Check alias resolution
    print()
    print("Alias Resolution:")
    print("-" * 50)
    for alias, target in router.alias_map.items():
        provider, model = router.resolve_alias(alias)
        routable = provider in router.adapters
        icon = "OK" if routable else "WARN"
        print(f"  [{icon:4s}] {alias:8s} -> {target:32s} {'(routable)' if routable else '(no adapter)'}")

    # 5. OpenAI live validation
    openai_live_ok = True
    if "openai" in router.adapters:
        print()
        print("OpenAI Live Validation:")
        print("-" * 50)
        openai_live_ok = asyncio.run(validate_openai_live(router))
    else:
        openai_live_ok = False

    # 6. Anthropic live validation
    anthropic_live_ok = True
    if "anthropic" in router.adapters:
        print()
        print("Anthropic Live Validation:")
        print("-" * 50)
        anthropic_live_ok = asyncio.run(validate_anthropic_live(router))
    else:
        anthropic_live_ok = False

    # 7. Summary
    print()
    print("=" * 60)
    if all_ok and openai_live_ok and anthropic_live_ok:
        print("WORKSPACE VALIDATION PASSED.")
        print("OpenAI and Anthropic passed live validation; Google is config-validated.")
    else:
        if not all_ok:
            print("SOME PROVIDERS ARE NOT CONFIGURED. Check .env keys above.")
        if not openai_live_ok:
            print("OPENAI LIVE VALIDATION FAILED. Check OPENAI_API_KEY scopes or model access.")
        if not anthropic_live_ok:
            print("ANTHROPIC LIVE VALIDATION FAILED. Check ANTHROPIC_API_KEY or model access.")
    print("=" * 60)

    return 0 if all_ok and openai_live_ok and anthropic_live_ok else 1


async def validate_openai_live(router):
    """Run a minimal real OpenAI request against the configured runtime path."""
    adapter = router.adapters["openai"]
    model = next(iter(adapter.config.get("models", {})), "gpt-5.4")

    try:
        result = await adapter.execute(
            model=model,
            system_prompt="Reply with exactly 4.",
            user_prompt="What is 2 + 2? Reply with exactly 4.",
            max_tokens=16,
            temperature=0.0,
        )
        content = (result.get("content") or "").strip()
        preview = content if len(content) <= 40 else content[:37] + "..."
        print(f"  [OK  ] openai       | model: {model:16s} | reply: {preview!r}")
        return True
    except Exception as exc:
        detail = classify_live_validation_error(exc)
        print(f"  [FAIL] openai       | model: {model:16s} | {detail}")
        return False


async def validate_anthropic_live(router):
    """Run a minimal real Anthropic request against the configured runtime path."""
    adapter = router.adapters["anthropic"]
    model = next(iter(adapter.config.get("models", {})), "claude-opus-4-6")

    try:
        result = await adapter.execute(
            model=model,
            system_prompt="Reply with exactly 4.",
            user_prompt="What is 2 + 2? Reply with exactly 4.",
            max_tokens=16,
            temperature=0.0,
        )
        content = (result.get("content") or "").strip()
        preview = content if len(content) <= 40 else content[:37] + "..."
        print(f"  [OK  ] anthropic    | model: {model:16s} | reply: {preview!r}")
        return True
    except Exception as exc:
        detail = classify_live_validation_error(exc)
        print(f"  [FAIL] anthropic    | model: {model:16s} | {detail}")
        return False


if __name__ == "__main__":
    sys.exit(main())
