"""Skill-to-model router with failover and cost tracking."""

import os
import yaml
import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from .base import SkillRequest, SkillResponse, CostRecord
from .anthropic_adapter import AnthropicAdapter
from .openai_adapter import OpenAIAdapter
from .google_adapter import GoogleAdapter


class SkillRouter:
    """Routes skill requests to the appropriate LLM provider."""

    def __init__(self, config_path: str = "adapters/config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.adapters = {}
        self._init_adapters()
        self.alias_map = self.config.get("alias_map", {})
        self.cost_config = self.config.get("cost", {})
        self.daily_cost = 0.0
        self.daily_cost_date = time.strftime("%Y-%m-%d")

    def _init_adapters(self):
        """Initialize provider adapters from config."""
        providers = self.config.get("providers", {})

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

    def load_krass_md(self) -> str:
        """Load KRASS.md cognitive profile."""
        krass_path = Path("KRASS.md")
        if krass_path.exists():
            return krass_path.read_text()
        return ""

    def _check_cost_budget(self, estimated_cost: float) -> bool:
        """Check if request is within cost budget."""
        today = time.strftime("%Y-%m-%d")
        if today != self.daily_cost_date:
            self.daily_cost = 0.0
            self.daily_cost_date = today

        max_per_request = self.cost_config.get("max_per_request", 1.00)
        max_per_day = self.cost_config.get("max_per_day", 50.00)

        if estimated_cost > max_per_request:
            return False
        if self.daily_cost + estimated_cost > max_per_day:
            return False
        return True

    async def execute(self, request: SkillRequest) -> SkillResponse:
        """Route and execute a skill request."""
        skill = self.load_skill(request.skill_id)
        krass_md = self.load_krass_md()
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
                continue

            adapter = self.adapters[provider_name]
            if not adapter.circuit_breaker.can_execute():
                continue

            system_prompt = adapter.build_system_prompt(prompt_md, krass_md)
            user_prompt = request.input_text

            try:
                result = await adapter.execute(
                    model=model_id,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    **request.options,
                )

                cost = adapter.estimate_cost(
                    result["input_tokens"],
                    result["output_tokens"],
                    model_id,
                )
                self.daily_cost += cost

                # Log cost
                record = CostRecord(
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    skill_id=request.skill_id,
                    model=model_id,
                    provider=provider_name,
                    input_tokens=result["input_tokens"],
                    output_tokens=result["output_tokens"],
                    cost=cost,
                    latency_ms=result["latency_ms"],
                )
                log_file = self.cost_config.get("log_file", "logs/cost.jsonl")
                adapter.log_cost(record, log_file)

                return SkillResponse(
                    output=json.loads(result["content"]) if result["content"].strip().startswith("{") else {"raw": result["content"]},
                    model_used=model_id,
                    provider=provider_name,
                    input_tokens=result["input_tokens"],
                    output_tokens=result["output_tokens"],
                    cost=cost,
                    latency_ms=result["latency_ms"],
                )

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(
            f"All models failed for skill {request.skill_id}: {last_error}"
        )
