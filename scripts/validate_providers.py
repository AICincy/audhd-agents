"""Validate provider configuration and optionally test live API connectivity.

Usage:
    python scripts/validate_providers.py --dry-run       # config-only validation
    python scripts/validate_providers.py                   # live API validation
    python scripts/validate_providers.py --providers openai # single provider
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.router import SkillRouter


async def validate_config(router: SkillRouter) -> list[dict[str, object]]:
    """Validate config without making API calls."""
    results = []

    # Check alias resolution
    for alias, full in router.alias_map.items():
        try:
            provider, model = router.resolve_alias(alias)
            has_adapter = provider in router.adapters
            results.append({
                "alias": alias,
                "provider": provider,
                "model": model,
                "adapter_loaded": has_adapter,
                "status": "OK" if has_adapter else "NO_ADAPTER",
                "error": None,
            })
        except Exception as e:
            results.append({
                "alias": alias,
                "provider": "?",
                "model": "?",
                "adapter_loaded": False,
                "status": "RESOLVE_FAILED",
                "error": str(e),
            })

    return results


async def validate_live(router: SkillRouter, providers: list[str]) -> list[dict[str, object]]:
    """Make a minimal API call per provider to confirm connectivity."""
    results = []

    # Pick one representative alias per provider
    provider_aliases: dict[str, str] = {}
    for alias, full in router.alias_map.items():
        if "/" in full:
            prov = full.split("/", 1)[0]
            if prov not in provider_aliases:
                provider_aliases[prov] = alias

    for provider, alias in provider_aliases.items():
        if providers and provider not in providers:
            continue
        if provider not in router.adapters:
            results.append({
                "alias": alias,
                "provider": provider,
                "status": "SKIPPED",
                "latency_ms": 0,
                "error": "No adapter loaded",
            })
            continue

        try:
            _, model = router.resolve_alias(alias)
            adapter = router.adapters[provider]
            start = time.time()
            response = await adapter.execute(
                model=model,
                system_prompt="You are a test assistant.",
                user_prompt="Reply with exactly: OK",
                max_tokens=16,
                temperature=0.0,
            )
            latency = int((time.time() - start) * 1000)
            content = response.get("content", "")
            results.append({
                "alias": alias,
                "provider": provider,
                "status": "OK" if content else "EMPTY_RESPONSE",
                "latency_ms": latency,
                "input_tokens": response.get("input_tokens", 0),
                "output_tokens": response.get("output_tokens", 0),
                "error": None,
            })
        except Exception as e:
            results.append({
                "alias": alias,
                "provider": provider,
                "status": "FAILED",
                "latency_ms": 0,
                "error": str(e),
            })

    return results


def print_table(results: list[dict[str, object]], title: str):
    """Print results as a formatted table."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")

    if not results:
        print("  No results.")
        return

    # Determine columns from first result
    cols = list(results[0].keys())
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in results)) for c in cols}

    # Header
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    print(f"  {header}")
    print(f"  {' | '.join('-' * widths[c] for c in cols)}")

    # Rows
    for r in results:
        row = " | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols)
        print(f"  {row}")

    # Summary
    ok = sum(1 for r in results if r.get("status") == "OK")
    total = len(results)
    print(f"\n  {ok}/{total} passed")


async def main():
    parser = argparse.ArgumentParser(description="Validate provider configuration")
    parser.add_argument("--dry-run", action="store_true", help="Config-only validation (no API calls)")
    parser.add_argument("--providers", type=str, default="", help="Comma-separated provider filter (e.g. openai,google)")
    args = parser.parse_args()

    providers = [p.strip() for p in args.providers.split(",") if p.strip()] if args.providers else []

    router = SkillRouter()

    # Always run config validation
    config_results = await validate_config(router)
    print_table(config_results, "Configuration Validation")

    if not args.dry_run:
        live_results = await validate_live(router, providers)
        print_table(live_results, "Live API Validation")

    # Exit code based on results
    all_results: list[dict[str, object]] = list(config_results)
    if not args.dry_run:
        all_results.extend(live_results)

    failures = [r for r in all_results if r.get("status") not in ("OK", "SKIPPED")]
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
