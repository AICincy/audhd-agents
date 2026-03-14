"""Skill-to-model router with failover and dotenv loading."""

import os
import yaml
import json
import asyncio
from pathlib import Path

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
            # Prefer the repo-local .env over inherited shell state so key updates
            # take effect deterministically in VS Code terminals and scripts.
            load_dotenv(override=True)
        else:
            import sys

            print(
                "Warning: python-dotenv not installed. "
                "Environment variables must be set manually. "
                "Run: pip install python-dotenv",
                file=sys.stderr,
            )

        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.adapters = {}
        self.adapter_init_errors = {}
        self.skill_map = {}
        self._build_skill_map()
        self._init_adapters()
        self.alias_map = self.config.get("alias_map", {})

    def _build_skill_map(self):
        """Build a map of skill_id to directory path for nested discovery."""
        skill_root = Path("skills")
        if not skill_root.exists():
            return
        for path in skill_root.rglob("skill.yaml"):
            try:
                with open(path, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    if cfg and "id" in cfg:
                        self.skill_map[cfg["id"]] = path.parent
            except Exception:
                continue

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
                self.adapters["anthropic"] = AnthropicAdapter(api_key=key, config=cfg)

        if "openai" in providers:
            cfg = providers["openai"]
            key = os.getenv(cfg.get("env_key", "OPENAI_API_KEY"))
            if key:
                self.adapters["openai"] = OpenAIAdapter(api_key=key, config=cfg)

        if "google" in providers:
            cfg = providers["google"]
            if GoogleAdapter.has_configuration(cfg):
                adapter = GoogleAdapter(config=cfg)
                if adapter.client:
                    self.adapters["google"] = adapter
                else:
                    self.adapter_init_errors["google"] = (
                        adapter.init_error or "Google adapter initialization failed"
                    )

    def resolve_alias(self, alias: str) -> tuple:
        """Resolve model alias to (provider, model_id)."""
        full = self.alias_map.get(alias, alias)
        if "/" in full:
            provider, model = full.split("/", 1)
            return provider, model
        return None, alias

    def load_skill(self, skill_id: str) -> dict:
        """Load skill configuration from skills directory (Synchronous)."""
        skill_dir = self.skill_map.get(skill_id)
        if not skill_dir:
            skill_dir = Path("skills") / skill_id

        with open(skill_dir / "skill.yaml", encoding="utf-8") as f:
            skill_config = yaml.safe_load(f)

        prompt_path = skill_dir / "prompt.md"
        # Blocking I/O
        prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

        schema_path = skill_dir / "schema.json"
        schema = {}
        if schema_path.exists():
            with open(schema_path, encoding="utf-8") as f:
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
            return profile_path.read_text(encoding="utf-8")
        return ""

    def load_skills_md(self) -> str:
        """Load SKILL.md cognitive support skills."""
        skills_path = Path("SKILL.md")
        if skills_path.exists():
            return skills_path.read_text(encoding="utf-8")
        return ""

    def load_model_md(self, provider: str) -> str:
        """Load provider-specific model instructions (e.g., models/OPENAI.md)."""
        model_map = {
            "openai": "models/OPENAI.md",
            "anthropic": "models/ANTHROPIC.md",
            "google": "models/GEMINI.md",
        }
        path_str = model_map.get(provider.lower())
        if path_str:
            path = Path(path_str)
            if path.exists():
                return path.read_text(encoding="utf-8")
        return ""

    def load_tool_md(self) -> str:
        """Load TOOL.md global tool definitions."""
        tool_path = Path("TOOL.md")
        if tool_path.exists():
            return tool_path.read_text(encoding="utf-8")
        return ""

    def get_status(self) -> dict:
        """Return adapter connectivity status for diagnostics.

        Usage:
            router = SkillRouter()
            print(json.dumps(router.get_status(), indent=2))
        """
        status = {}
        for name, adapter in self.adapters.items():
            api_key = getattr(adapter, "api_key", None)
            key_preview = api_key[:8] + "..." if api_key else None
            status[name] = {
                "connected": bool(getattr(adapter, "client", None)),
                "key_prefix": key_preview,
                "circuit_breaker": adapter.circuit_breaker.state,
                "models": list(adapter.config.get("models", {}).keys()),
            }
            if getattr(adapter, "backend", None):
                status[name]["backend"] = adapter.backend
            if getattr(adapter, "auth_mode", None):
                status[name]["auth_mode"] = adapter.auth_mode
            if getattr(adapter, "project", None):
                status[name]["project"] = adapter.project
            if getattr(adapter, "location", None):
                status[name]["location"] = adapter.location
            if getattr(adapter, "init_error", None):
                status[name]["error"] = adapter.init_error
        # Report providers configured but missing keys
        for provider in self.config.get("providers", {}):
            if provider not in status:
                env_key = self.config["providers"][provider].get("env_key", "")
                error = self.adapter_init_errors.get(provider)
                if not error and provider == "google":
                    error = (
                        "Set GOOGLE_API_KEY for Gemini Developer API, or "
                        "set VERTEX_API_KEY / GOOGLE_GENAI_USE_VERTEXAI for Vertex AI"
                    )
                elif not error:
                    error = f"API key not found. Set {env_key} in .env"
                status[provider] = {
                    "connected": False,
                    "key_prefix": None,
                    "circuit_breaker": "n/a",
                    "models": [],
                    "error": error,
                }
        return status

    async def _load_instruction_stack(self, provider_name: str) -> str:
        """Offload blocking I/O to a thread to keep the event loop responsive."""
        loop = asyncio.get_running_loop()
        profile = await loop.run_in_executor(None, self.load_profile_md)
        model_md = await loop.run_in_executor(None, self.load_model_md, provider_name)
        skills_md = await loop.run_in_executor(None, self.load_skills_md)
        tool_md = await loop.run_in_executor(None, self.load_tool_md)

        stack = [profile, model_md, skills_md, tool_md]
        return "\n\n".join(filter(None, stack))

    async def execute(self, request: SkillRequest) -> SkillResponse:
        """Route and execute a skill request."""
        # Offload initial skill loading which involves multiple files
        loop = asyncio.get_running_loop()
        skill = await loop.run_in_executor(None, self.load_skill, request.skill_id)

        skill_config = skill["config"]
        prompt_md = skill["prompt"]

        # Determine model chain: override > primary > fallback
        if request.model_override:
            model_chain = [request.model_override]
        else:
            primary = skill_config.get("models", {}).get("primary", "G-PRO")
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
                last_error = RuntimeError(f"Circuit breaker open for {provider_name}")
                continue

            # Non-blocking load of the rest of the stack
            combined_instructions = await self._load_instruction_stack(provider_name)
            system_prompt = adapter.build_system_prompt(
                prompt_md, combined_instructions
            )
            user_prompt = request.input_text

            try:
                result = await adapter.execute(
                    model=model_id,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    **request.options,
                )

                # Safely parse JSON if possible
                content = result.get("content", "").strip()
                output = {"raw": content}

                if content.startswith(("{", "[")):
                    try:
                        # Offload heavy JSON parsing for large responses (>10KB)
                        if len(content) > 10000:
                            output = await loop.run_in_executor(
                                None, json.loads, content
                            )
                        else:
                            output = json.loads(content)
                    except json.JSONDecodeError:
                        output = {"raw": content, "error": "JSON parse failed"}

                return SkillResponse(
                    output=output,
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
