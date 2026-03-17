"""Multi-provider LLM client with model alias routing.

Routes skill model aliases (G-PRO, O-54P, etc.) to the correct
API provider (Google Generative AI, OpenAI) and model name.

Configuration:
    MODEL_MAP: alias -> (provider, api_model_name)
    Env vars: GOOGLE_API_KEY, OPENAI_API_KEY
    Override: SK_MODEL_MAP_FILE env var pointing to a JSON override file.
             The file must be a regular file located within the project root
             directory (parent of cli/). Paths outside the project root are
             ignored and a warning is emitted to stderr to prevent path-traversal attacks.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# ── Model alias map ──────────────────────────────────────────────
# Keys: aliases used in skill.yaml `models.primary` / `models.fallback`
# Values: (provider, api_model_name)
#
# Update these when new models ship. Or set SK_MODEL_MAP_FILE to a
# JSON file with the same structure: {"ALIAS": ["provider", "model"]}.
MODEL_MAP: dict[str, tuple[str, str]] = {
    # Google
    "G-PRO31":  ("google", "gemini-2.5-pro"),
    "G-PRO":    ("google", "gemini-2.5-pro"),
    "G-FLASH":  ("google", "gemini-2.5-flash"),
    # OpenAI
    "O-54P":    ("openai", "gpt-4o"),
    "O-54":     ("openai", "gpt-4o"),
    "O-O4M":    ("openai", "o4-mini"),
}


def _load_model_map() -> dict[str, tuple[str, str]]:
    """Load MODEL_MAP with optional override from SK_MODEL_MAP_FILE."""
    override_path = os.environ.get("SK_MODEL_MAP_FILE")
    if override_path:
        from pathlib import Path
        resolved = Path(override_path).resolve()
        if not resolved.is_file():
            return MODEL_MAP
        project_root = Path(__file__).resolve().parent.parent
        try:
            resolved.relative_to(project_root)
        except ValueError:
            print(
                f"Warning: SK_MODEL_MAP_FILE path '{override_path}' is outside project root, ignoring",
                file=sys.stderr,
            )
            return MODEL_MAP
        with open(resolved, encoding="utf-8") as f:
            raw = json.load(f)
        merged = dict(MODEL_MAP)
        for alias, pair in raw.items():
            merged[alias] = tuple(pair)  # type: ignore[arg-type]
        return merged
    return MODEL_MAP


def resolve_model(alias: str) -> tuple[str, str]:
    """Resolve model alias to (provider, model_name)."""
    mmap = _load_model_map()
    if alias in mmap:
        return mmap[alias]
    # Guess provider from alias prefix
    if alias.startswith(("gemini", "G-")):
        return ("google", alias)
    if alias.startswith(("gpt", "o4", "O-", "o1", "o3")):
        return ("openai", alias)
    # Default fallback
    print(f"Warning: unknown model '{alias}', defaulting to gemini-2.5-flash", file=sys.stderr)
    return ("google", "gemini-2.5-flash")


def call_llm(model_alias: str, system_prompt: str, user_message: str) -> str:
    """Route LLM call to correct provider based on model alias."""
    provider, model = resolve_model(model_alias)
    if provider == "google":
        return _call_google(model, system_prompt, user_message)
    elif provider == "openai":
        return _call_openai(model, system_prompt, user_message)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _call_google(model: str, system_prompt: str, user_message: str) -> str:
    """Call Google Generative AI API."""
    try:
        import google.generativeai as genai
    except ImportError:
        print(
            "Error: google-generativeai not installed.\n"
            "  pip install google-generativeai",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY env var not set", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt,
    )
    response = gen_model.generate_content(user_message)
    return response.text


def _call_openai(model: str, system_prompt: str, user_message: str) -> str:
    """Call OpenAI Chat Completions API."""
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "Error: openai not installed.\n"
            "  pip install openai",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY env var not set", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""
