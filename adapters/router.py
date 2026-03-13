"""Skill-to-model router with failover and dotenv loading."""

import os
import yaml
import json
import time
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from .base import SkillRequest, SkillResponse, CostRecord
from .anthropic_adapter import AnthropicAdapter
from .openai_adapter import OpenAIAdapter
from .google_adapter import GoogleAdapter


class SkillRouter:
    """Routes skill requests to the appropriate LLM provider."""

    def __init__(self, config_path: str = "adapters/config.yaml"):
        # Load .env file into os.environ
        if load_dotenv:
            load_dotenv()
        else:
            import sys
            print(
                "Warning: python-dotenv not installed. "
                "Environment variables must be set manually. "
                "Run: pip install python-dotenv",
                file=sys.stderr,
            )

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.adapters = {}
        self._init_adapters()
        self.alias_map = self.config.get("alias_map", {})

    def _init_adapters(self):
        """Initialize provider adapters from config with circuit breaker settings."""
        providers = self.config.get("providers", {})
        cb_cfg = self.config.get("circuit_breaker", {})

        # Merge top-level circuit breaker config into each provider
        for cfg in providers.values():
            cfg.setdefault("failure_threshold", cb_cfg.get("failure_threshold", 3))
            cfg.setdefault("recovery_timeout", cb_cfg.get("recovery_timeout", 60))

        if "anthropic" in providers:
            cfg = providers["anthropic"]
            key = os.getenv(cfg.get("env_key", "ANTHROPIC_API_KEY"))
            if key:
                self.adapters["anthropic"] = AnthropicAdapter(
                    api_key=key, config=cfg
                )

        if "openai" in providers:
            cfg = providers["openai"]
            key = os.getenv(cfg.get("env_key", "OPENAI_API_KEY"))
            if key:
                self.adapters["openai"] = OpenAIAdapter(
                    api_key=key, config=cfg
                )

        if "google" in providers:
            cfg = providers["google"]
            key = os.getenv(cfg.get("env_key", "GOOGLE_API_KEY"))
            if key:
                self.adapters["google"] = GoogleAdapter(
                    api_key=key, config=cfg
                )

    def resolve_alias(self, alias: str) -> tuple:
        """Resolve model alias to (provider, model_id)."""
        full = self.alias_map.get(alias, alias)
        if "/" in full:
            provider, model = full.split("/", 1)
            return provider, model
        return None, alias

    def load_skill(self, skill_id: str) -> dict:
        """Load skill configuration from skills directory."""
        skill_dir = Path("skills") / skill_id
        with open(skill_dir / "skill.yaml") as f:
            skill_config = yaml.safe_load(f)
        with open(skill_dir / "prompt.md") as f:
            prompt = f.read()
        with open(skill_dir / "schema.json") as f:
            schema = json.load(f)
        return {
            "config": skill_config,
            "prompt": prompt,
            "schema": schema,
        }

    def load_profile_md(self) -> str:
        """Load PROFILE.md cognitive profile."""
        profile_path = Path("PROFILE.md")
        if profile_path.exists():
            return profile_path.read_text()
        return ""

    def get_status(self) -> dict:
        """Return adapter connectivity status for diagnostics.

        Usage:
            router = SkillRouter()
            print(json.dumps(router.get_status(), indent=2))
        """
        status = {}
        for name, adapter in self.adapters.items():
            key_preview = adapter.api_key[:8] + "..." if adapter.api_key else None
            status[name] = {
                "connected": bool(adapter.api_key),
                "key_prefix": key_preview,
                "circuit_breaker": adapter.circuit_breaker.state,
                "models": list(adapter.config.get("models", {}).keys()),
            }
        # Report providers configured but missing keys
        for provider in self.config.get("providers", {}):
            if provider not in status:
                env_key = self.config["providers"][provider].get("env_key", "")
                status[provider] = {
                    "connected": False,
                    "key_prefix": None,
                    "circuit_breaker": "n/a",
                    "models": [],
                    "error": f"API key not found. Set {env_key} in .env",
                }
        return status

    async def execute(self, request: SkillRequest) -> SkillResponse:
        """Route and execute a skill request."""
        skill = self.load_skill(request.skill_id)
        profile_md = self.load_profile_md()
        skill_config = skill["config"]
        prompt_md = skill["prompt"]

        # Determine model chain: override > primary > fallback
        if request.model_override:
            model_chain = [request.model_override]
        else:
            primary = skill_config.get("models", {}).get("primary", "C-OP46")
            fallback = skill_config.get("models", {}).get("fallback", [])
            model_chain = [primary] + fallback

        last_error = None
        for alias in model_chain:
            provider_name, model_id = self.resolve_alias(alias)
            if provider_name not in self.adapters:
                last_error = RuntimeError(
                    f"Provider '{provider_name}' not available for alias '{alias}'. "
                    f"Check API key in .env"
                )
                continue

            adapter = self.adapters[provider_name]
            if not adapter.circuit_breaker.can_execute():
                last_error = RuntimeError(
                    f"Circuit breaker open for {provider_name}"
                )
                continue

            system_prompt = adapter.build_system_prompt(prompt_md, profile_md)
            user_prompt = request.input_text

            try:
                result = await adapter.execute(
                    model=model_id,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    **request.options,
                )

                return SkillResponse(
                    output=(
                        json.loads(result["content"])
                        if result["content"].strip().startswith("{")
                        else {"raw": result["content"]}
                    ),
                    model_used=model_id,
                    provider=provider_name,
                    input_tokens=result["input_tokens"],
                    output_tokens=result["output_tokens"],
                    latency_ms=result["latency_ms"],
                )

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(
            f"All models failed for skill {request.skill_id}: {last_error}"
        )
