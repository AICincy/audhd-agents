#!/usr/bin/env python3
"""Smoke-test the private runtime endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_ALIASES = ["G-PRO31", "G-FLA31", "O-54"]


def call_json(method: str, url: str, body: dict | None = None, token: str | None = None):
    """Make an HTTP request and return the decoded JSON response."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read().decode("utf-8")
        return response.status, json.loads(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the operator runtime.")
    parser.add_argument("--base-url", required=True, help="Runtime base URL")
    parser.add_argument(
        "--skill-id",
        default="agents-orchestrator",
        help="Existing skill ID to invoke during live smoke tests",
    )
    parser.add_argument(
        "--model-alias",
        action="append",
        dest="model_aliases",
        default=[],
        help="Model alias to test through /execute. Repeat for multiple providers.",
    )
    parser.add_argument(
        "--input-text",
        default="Summarize this workflow in one sentence and keep the response compact.",
        help="Prompt sent to the selected skill",
    )
    parser.add_argument(
        "--token-env",
        default="SERVICE_AUTH_TOKEN",
        help="Environment variable containing the bearer token for the private service",
    )
    args = parser.parse_args()

    token = os.getenv(args.token_env)
    aliases = args.model_aliases or DEFAULT_ALIASES
    base_url = args.base_url.rstrip("/")

    try:
        status_code, health = call_json("GET", f"{base_url}/healthz", token=token)
        if status_code != 200 or health.get("status") != "ok":
            raise RuntimeError(f"/healthz failed: {health}")

        status_code, ready = call_json("GET", f"{base_url}/readyz", token=token)
        if status_code != 200 or ready.get("status") != "ready":
            raise RuntimeError(f"/readyz failed: {ready}")

        for alias in aliases:
            status_code, response = call_json(
                "POST",
                f"{base_url}/execute",
                body={
                    "skill_id": args.skill_id,
                    "input_text": args.input_text,
                    "model_override": alias,
                    "request_id": f"smoke-{alias.lower()}",
                },
                token=token,
            )
            if status_code != 200:
                raise RuntimeError(f"/execute failed for {alias}: {response}")
            if not response.get("provider") or not response.get("model_used"):
                raise RuntimeError(f"Incomplete execute response for {alias}: {response}")

        print("Runtime smoke test passed.")
        return 0
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - exercised in CI/runtime
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
