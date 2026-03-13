#!/usr/bin/env python3
"""Connection diagnostics for audhd-agents.

Run from repo root:
    python scripts/check_connections.py

Checks:
  1. .env file exists and is loaded
  2. All 3 provider API keys are present
  3. Adapter initialization succeeds
  4. Model routing resolves all 11 aliases
"""

import sys
import json
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    print("=" * 60)
    print("AUDHD-AGENTS CONNECTION CHECK")
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

    # 3. Check adapter status
    print()
    print("Provider Status:")
    print("-" * 50)
    status = router.get_status()
    all_ok = True
    for provider, info in status.items():
        connected = info["connected"]
        icon = "OK" if connected else "FAIL"
        key_info = f"key: {info['key_prefix']}" if info.get("key_prefix") else "no key"
        models = ", ".join(info.get("models", [])) or "none"
        print(f"  [{icon:4s}] {provider:12s} | {key_info:24s} | models: {models}")
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

    # 5. Summary
    print()
    print("=" * 60)
    if all_ok:
        print("ALL PROVIDERS CONNECTED. Ready to execute skills.")
    else:
        print("SOME PROVIDERS MISSING. Check .env keys above.")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
