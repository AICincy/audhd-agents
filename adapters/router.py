"""Skill-to-model router with failover, cognitive pipeline, and dotenv loading."""

import os
import yaml
import json
import asyncio
import logging
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from .base import SkillRequest, SkillResponse, CostRecord
from .anthropic_adapter import AnthropicAdapter
from .openai_adapter import OpenAIAdapter
from .google_adapter import GoogleAdapter

# Cognitive pipeline imports (A-2, A-3, A-4, A-6)
from runtime.cognitive import (
    CognitiveState,
    parse_cognitive_state,
    infer_mode,
    filter_model_chain,
    build_cognitive_preamble,
)
from runtime.hooks import run_hooks, HookContext
from runtime.validation import validate_output

logger = logging.getLogger("audhd_agents.router")


class SkillRouter:
    """Routes skill requests to the appropriate LLM provider.

    Integrates cognitive pipeline (A-3), sk_hooks (A-4), and
    output validation (A-6) into the execution flow.
    """

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
            # Skip _base directory (shared templates, not a skill)
            if "_base" in path.parts:
                continue
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

    def load_prompt_base(self) -> str:
        """Load shared prompt base template (A-5)."""
        base_path = Path("skills/_base/prompt_base.md")
        if base_path.exists():
            return base_path.read_text(encoding="utf-8")
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
        """Offload blocking I/O to a thread to keep the event loop responsive.

        Stack order: PROFILE.md > prompt_base.md > model MD > SKILL.md > TOOL.md
        The shared prompt base (A-5) is loaded between PROFILE.md and model MD.
        """
        loop = asyncio.get_running_loop()
        profile = await loop.run_in_executor(None, self.load_profile_md)
        prompt_base = await loop.run_in_executor(None, self.load_prompt_base)
        model_md = await loop.run_in_executor(None, self.load_model_md, provider_name)
        skills_md = await loop.run_in_executor(None, self.load_skills_md)
        tool_md = await loop.run_in_executor(None, self.load_tool_md)

        stack = [profile, prompt_base, model_md, skills_md, tool_md]
        return "\n\n".join(filter(None, stack))

    async def execute(self, request: SkillRequest) -> SkillResponse:
        """Route and execute a skill request with cognitive pipeline.

        Execution flow:
        1. Parse cognitive state from request options (A-3)
        2. Auto-infer mode from input if not provided (PROFILE.md)
        3. Load skill config and prompt
        4. Build model chain and filter by energy level (AGENT.md)
        5. Run sk_hooks pre-processing (A-4)
        6. Build cognitive preamble and inject into prompt (A-2)
        7. Execute against model chain with failover
        8. Validate output against cognitive contract (A-6)
        9. Return response with validation metadata
        """
        # Step 1: Parse cognitive state (A-3)
        cognitive_state = parse_cognitive_state(request.options)

        # Step 2: Auto-infer mode if not set
        if not cognitive_state.active_mode or cognitive_state.active_mode == "execute":
            inferred = infer_mode(request.input_text)
            if inferred != "execute":
                cognitive_state.active_mode = inferred

        # Step 3: Load skill (offload blocking I/O)
        loop = asyncio.get_running_loop()
        skill = await loop.run_in_executor(None, self.load_skill, request.skill_id)

        skill_config = skill["config"]
        prompt_md = skill["prompt"]

        # Step 4: Build and filter model chain
        if request.model_override:
            model_chain = [request.model_override]
        else:
            primary = skill_config.get("models", {}).get("primary", "G-PRO")
            fallback = skill_config.get("models", {}).get("fallback", [])
            model_chain = [primary] + fallback

        # Energy-adaptive model filtering (AGENT.md)
        model_chain = filter_model_chain(model_chain, cognitive_state, self.alias_map)

        # Crash mode: no new tasks
        if not model_chain and cognitive_state.is_crash:
            return SkillResponse(
                output={
                    "raw": (
                        "Everything is saved. Nothing is urgent. "
                        "Come back when ready."
                    ),
                    "cognitive_state": {"energy_level": "crash", "output_mode": "crash"},
                },
                model_used="none",
                provider="cognitive_pipeline",
                input_tokens=0,
                output_tokens=0,
                latency_ms=0,
            )

        if not model_chain:
            raise RuntimeError(
                f"No models available for skill {request.skill_id} at "
                f"energy level '{cognitive_state.energy_level}'"
            )

        # Step 5: Run sk_hooks pre-processing (A-4)
        hook_names = skill_config.get("sk_hooks", [])
        if hook_names:
            hook_ctx = HookContext(
                skill_id=request.skill_id,
                cognitive_state=cognitive_state,
                input_text=request.input_text,
                prompt=prompt_md,
                options=request.options,
            )
            hook_result = run_hooks(hook_names, hook_ctx)

            if hook_result.modified_prompt:
                prompt_md = hook_result.modified_prompt
            if hook_result.modified_input:
                request = SkillRequest(
                    skill_id=request.skill_id,
                    input_text=hook_result.modified_input,
                    options=request.options,
                    model_override=request.model_override,
                )
            if hook_result.validation_warnings:
                logger.warning(
                    "Hook warnings for %s: %s",
                    request.skill_id,
                    hook_result.validation_warnings,
                )

        # Step 6: Build cognitive preamble (A-2)
        cognitive_preamble = build_cognitive_preamble(cognitive_state)

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

            # Non-blocking load of the instruction stack
            combined_instructions = await self._load_instruction_stack(provider_name)
            system_prompt = adapter.build_system_prompt(
                prompt_md, combined_instructions
            )

            # Inject cognitive preamble at the top of system prompt
            system_prompt = cognitive_preamble + "\n\n" + system_prompt

            # Audit correlation ID
            audit_id = f"audit-{request.skill_id}-{os.getpid()}"
            user_prompt = f"[AUDIT_ID: {audit_id}]\n{request.input_text}"
            request.options.setdefault("headers", {}).update({"X-Audit-ID": audit_id})

            try:
                result = await adapter.execute(
                    model=model_id,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    **request.options,
                )

                # SK-SYS-RECOVER: Autonomous backoff detection
                if result.get("headers", {}).get("x-backoff") == "true":
                    await asyncio.sleep(2.0)
                    result["content"] = f"[RECOVERY_ACTIVE] {result.get('content')}"

                # Parse JSON output
                content = result.get("content", "").strip()
                output = {"raw": content}

                if content.startswith(("{", "[")):
                    try:
                        if len(content) > 10000:
                            output = await loop.run_in_executor(
                                None, json.loads, content
                            )
                        else:
                            output = json.loads(content)
                    except json.JSONDecodeError:
                        output = {"raw": content, "error": "JSON parse failed"}

                # Step 8: Validate output against cognitive contract (A-6)
                validation = validate_output(
                    content,
                    active_mode=cognitive_state.active_mode,
                    energy_level=cognitive_state.energy_level,
                    task_tier=cognitive_state.task_tier,
                )

                if not validation.passed:
                    logger.warning(
                        "Output validation failed for %s: %s",
                        request.skill_id,
                        validation.violations,
                    )
                    # Attach validation metadata to output (transparent, not opaque)
                    if isinstance(output, dict):
                        output["_validation"] = {
                            "passed": validation.passed,
                            "violations": validation.violations,
                            "warnings": validation.warnings,
                        }

                elif validation.warnings:
                    if isinstance(output, dict):
                        output["_validation"] = {
                            "passed": True,
                            "warnings": validation.warnings,
                        }

                return SkillResponse(
                    output=output,
                    model_used=model_id,
                    provider=provider_name,
                    headers=result.get("headers", {}),
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
