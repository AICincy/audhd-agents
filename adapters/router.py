"""Skill-to-model router with failover, cognitive pipeline, and dotenv loading."""

import os
import yaml
import json
import asyncio
import logging
import re
import uuid
import copy
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from .base import SkillRequest, SkillResponse, CostRecord
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
from runtime.planner import RuntimePlanner

logger = logging.getLogger("audhd_agents.router")


class SkillRouter:
    """Routes skill requests to the appropriate LLM provider.

    Integrates cognitive pipeline (A-3), sk_hooks (A-4), and
    output validation (A-6) into the execution flow.
    """

    def __init__(self, config_path: Optional[str] = None):
        if not config_path:
            config_path = str(Path(__file__).parent / "config.yaml")

        self.planner = RuntimePlanner()
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
            self.config: Dict[str, Any] = yaml.safe_load(f)

        self.adapters: Dict[str, Any] = {}
        self.adapter_init_errors: Dict[str, str] = {}
        self.skill_map: Dict[str, Path] = {}
        self.skill_capabilities: Dict[str, list[str]] = {}
        self._build_skill_map()
        self._init_adapters()
        self.alias_map = self.config.get("alias_map", {})

    def _build_skill_map(self):
        """Build a map of skill_id to directory path across for nested discovery."""
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
                    if cfg and "name" in cfg:
                        name = cfg["name"]
                        self.skill_map[name] = path.parent
                        self.skill_capabilities[name] = cfg.get("capabilities", [])
            except Exception as e:
                logger.error("Failed to load skill at %s: %s", path, e)
                continue

    def _init_adapters(self):
        """Initialize provider adapters from config with circuit breaker settings."""
        providers = self.config.get("providers", {})
        cb_cfg = self.config.get("circuit_breaker", {})

        # Merge top-level circuit breaker config into each provider
        for cfg in providers.values():
            cfg.setdefault("failure_threshold", cb_cfg.get("failure_threshold", 3))
            cfg.setdefault("recovery_timeout", cb_cfg.get("recovery_timeout", 60))

        if "openai" in providers:
            cfg = providers["openai"]
            raw_key = os.getenv(cfg.get("env_key", "OPENAI_API_KEY"))
            if raw_key:
                from pydantic import SecretStr
                self.adapters["openai"] = OpenAIAdapter(
                    api_key=SecretStr(raw_key), config=cfg
                )

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
        """Resolve model alias to (provider, model_id).

        In production (APP_ENV=production), if the resolved model has a
        production_fallback configured, transparently swap to the stable model.
        """
        full = self.alias_map.get(alias, alias)
        if "/" in full:
            provider, model = full.split("/", 1)
            # Auto-downgrade preview models in production
            if os.getenv("APP_ENV") == "production":
                provider_cfg = self.config.get("providers", {}).get(provider, {})
                model_cfg = provider_cfg.get("models", {}).get(model, {})
                fallback = model_cfg.get("production_fallback")
                if fallback:
                    logger.info(
                        "Production fallback: %s -> %s (preview model downgraded)",
                        model, fallback,
                    )
                    model = fallback
            return provider, model
        raise ValueError(f"Could not resolve alias '{alias}' to a provider/model pair. Check alias_map in config.yaml.")

    def load_skill(self, skill_id: str) -> dict:
        """Load skill configuration from skills directory (Synchronous)."""
        skill_dir = self.skill_map.get(skill_id)
        if not skill_dir:
            skill_dir = Path("skills") / skill_id

        try:
            with open(skill_dir / "skill.yaml", encoding="utf-8") as f:
                skill_config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Skill '{skill_id}' not found or missing skill.yaml at {skill_dir}")

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
        status: Dict[str, Any] = {}
        for name, adapter in self.adapters.items():
            api_key = getattr(adapter, "api_key", None)
            key_preview = "********" + api_key[-4:] if api_key and len(api_key) >= 4 else None
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
        providers_dict = self.config.get("providers", {})
        if isinstance(providers_dict, dict):
            for provider, p_config in providers_dict.items():
                p_str = str(provider)
                if p_str not in status:
                    env_key = p_config.get("env_key", "") if isinstance(p_config, dict) else ""
                    error = self.adapter_init_errors.get(p_str)
                    if not error and p_str == "google":
                        error = (
                            "Set GOOGLE_API_KEY for Gemini Developer API, or "
                            "set VERTEX_API_KEY / GOOGLE_GENAI_USE_VERTEXAI for Vertex AI"
                        )
                    elif not error:
                        error = f"API key not found. Set {env_key} in .env"
                    status[p_str] = {
                        "connected": False,
                        "key_prefix": None,
                        "circuit_breaker": "n/a",
                        "models": [],
                        "error": error,
                    }
        return status

    async def _load_instruction_stack(self, provider_name: str, needs_tools: bool = False) -> str:
        """Offload blocking I/O to a thread to keep the event loop responsive.

        Stack order: PROFILE.md > prompt_base.md > model MD > SKILL.md > TOOL.md
        The shared prompt base (A-5) is loaded between PROFILE.md and model MD.
        """
        loop = asyncio.get_running_loop()
        profile = await loop.run_in_executor(None, self.load_profile_md)  # type: ignore[arg-type]
        prompt_base = await loop.run_in_executor(None, self.load_prompt_base)  # type: ignore[arg-type]
        model_md = await loop.run_in_executor(None, self.load_model_md, provider_name)  # type: ignore[arg-type]
        skills_md = await loop.run_in_executor(None, self.load_skills_md)  # type: ignore[arg-type]
        tool_md = await loop.run_in_executor(None, self.load_tool_md) if needs_tools else ""  # type: ignore[arg-type]

        stack = [profile, prompt_base, model_md, skills_md, tool_md]
        return "\n\n".join(filter(None, stack))

    async def execute(self, request: SkillRequest, cognitive_state_override=None) -> SkillResponse:
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

        P1-1: Accepts cognitive_state_override from runtime.schemas.CognitiveState.
        When provided, its values are injected into request options for
        parse_cognitive_state compatibility.
        """
        # P1-1: Accept cognitive_state from runtime.schemas.CognitiveState
        if cognitive_state_override is not None:
            el = cognitive_state_override.energy_level
            request.options["energy_level"] = el.value if hasattr(el, "value") else str(el)
            att = cognitive_state_override.attention_state
            request.options["attention_state"] = att.value if hasattr(att, "value") else str(att)
            sc = cognitive_state_override.session_context
            request.options["session_context"] = sc.value if hasattr(sc, "value") else str(sc)

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
            needs_tools = bool(skill_config.get("tools"))
            combined_instructions = await self._load_instruction_stack(provider_name, needs_tools)
            system_prompt = adapter.build_system_prompt(
                prompt_md, combined_instructions
            )

            # Inject cognitive preamble at the top of system prompt
            system_prompt = cognitive_preamble + "\n\n" + system_prompt

            # Audit correlation ID (uniqueness fix)
            hex_id = uuid.uuid4().hex
            audit_id = f"audit-{request.skill_id}-{os.getpid()}-{hex_id[0:8]}"
            user_prompt = f"[AUDIT_ID: {audit_id}]\n{request.input_text}"

            # Deep copy to prevent state pollution across failovers
            req_options = copy.deepcopy(request.options)
            req_options.setdefault("headers", {}).update({"X-Audit-ID": audit_id})

            try:
                result = await adapter.execute(
                    model=model_id,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    **req_options,
                )

                # SK-SYS-RECOVER: Autonomous backoff detection
                if result.get("headers", {}).get("x-backoff") == "true":
                    import random
                    await asyncio.sleep(min(2.0 + random.random(), 5.0))
                    result["content"] = f"[RECOVERY_ACTIVE] {result.get('content')}"

                # Parse JSON output
                content = result.get("content", "").strip()
                output = {"raw": content}

                # Robust multi-strategy JSON extraction
                # Strategy 1: Extract from markdown code blocks (```json ... ```)
                json_content = None
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content, flags=re.IGNORECASE)
                if json_match:
                    json_content = json_match.group(1).strip()

                # Strategy 2: Bracket-match fallback (first '{' to last '}')
                if not json_content or not json_content.startswith(("{", "[")):
                    first_brace = content.find("{")
                    first_bracket = content.find("[")
                    candidates = [i for i in (first_brace, first_bracket) if i >= 0]
                    if candidates:
                        start_idx = min(candidates)
                        open_char = content[start_idx]
                        close_char = "}" if open_char == "{" else "]"
                        last_close = content.rfind(close_char)
                        if last_close > start_idx:
                            json_content = content[start_idx:last_close + 1].strip()

                # Strategy 3: Fall through to raw content
                if not json_content:
                    json_content = content.strip()

                if json_content.startswith(("{", "[")):
                    try:
                        if len(json_content) > 10000:
                            output = await loop.run_in_executor(
                                None, json.loads, json_content
                            )
                        else:
                            output = json.loads(json_content)
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
                    input_tokens=result.get("input_tokens", 0),
                    output_tokens=result.get("output_tokens", 0),
                    latency_ms=result.get("latency_ms", 0.0),
                )

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(
            f"All models failed for skill {request.skill_id}: {last_error}"
        )

    async def execute_chain(self, request: SkillRequest, cognitive_state_override=None) -> SkillResponse:
        """Route and execute a chain of skills based on capability planning.

        Execution flow:
        1. Leverage RuntimePlanner to determine capability chain from input.
        2. Resolve capabilities to specific skill IDs.
        3. Execute the chain sequentially, bridging state.
        """
        # P1-1: Accept cognitive_state from runtime.schemas.CognitiveState
        if cognitive_state_override is not None:
            el = cognitive_state_override.energy_level
            request.options["energy_level"] = el.value if hasattr(el, "value") else str(el)
            att = cognitive_state_override.attention_state
            request.options["attention_state"] = att.value if hasattr(att, "value") else str(att)
            sc = cognitive_state_override.session_context
            request.options["session_context"] = sc.value if hasattr(sc, "value") else str(sc)

        cognitive_state = parse_cognitive_state(request.options)

        # Infer mode to help the planner or hooks later
        if not cognitive_state.active_mode or cognitive_state.active_mode == "execute":
            inferred = infer_mode(request.input_text)
            if inferred != "execute":
                cognitive_state.active_mode = inferred

        # Use planner to parse intentions and determine capability chain
        capabilities = self.planner.plan_execution_chain(request.input_text)
        if not capabilities:
            raise ValueError(f"Planner could not determine a capability chain for the given input.")

        logger.info(f"Planned capability chain: {capabilities}")

        skills_to_run = []
        for cap in capabilities:
            skill_id = self.planner.resolve_capability_to_skill(cap, self.skill_capabilities)
            if not skill_id:
                raise ValueError(f"Planner could not resolve capability '{cap}' to a known skill.")
            skills_to_run.append(skill_id)

        logger.info(f"Resolved skill chain: {skills_to_run}")

        current_input = request.input_text
        last_response = None

        for idx, skill_id in enumerate(skills_to_run):
            logger.info(f"Executing step {idx+1}/{len(skills_to_run)}: {skill_id} (Capability: {capabilities[idx]})")

            step_request = SkillRequest(
                skill_id=skill_id,
                input_text=current_input,
                options=request.options.copy(),
                model_override=request.model_override
            )

            step_response = await self.execute(step_request, cognitive_state_override)
            last_response = step_response

            # Simple state bridge (SK-BRIDGE concept) with JSON safe wrapper
            raw_output = step_response.output.get("raw", "")
            current_input = json.dumps({
                "previous_step_output": {"skill": skill_id, "output": raw_output},
                "original_request": request.input_text
            }, ensure_ascii=False)

        if last_response is None:
            raise RuntimeError("Execution chain completed but no response was generated.")

        return last_response
