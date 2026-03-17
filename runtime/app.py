"""Private FastAPI runtime for operator-driven skill execution.

P1-1: Added cognitive_state to /execute request schema.
P2-1: Added webhook endpoints, auth middleware, structured logging.
P2-2: Added pipeline bridge initialization for webhook -> skill routing.

Endpoints:
    GET  /healthz              Liveness probe
    GET  /readyz               Readiness probe (provider checks)
    POST /execute              Skill execution with cognitive state
    POST /webhooks/notion      Notion webhook receiver (HMAC verified)
    GET  /webhooks/notion      Webhook subsystem health
    POST /webhooks/test        Dev echo endpoint (staging only)
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

import asyncio
import os

from fastapi import Depends, FastAPI, HTTPException, Request, status

from adapters.base import SkillRequest
from adapters.router import SkillRouter
from runtime.config import RuntimeSettings
from runtime.sanitize import sanitize_input

# P1-1: Cognitive state schemas
from runtime.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    CrashStateResponse,
    CognitiveCompliance,
    EnergyLevel,
)

# P2-1: Webhook and middleware imports
from runtime.webhooks import router as webhook_router
from runtime.middleware import register_middleware

# P2-2: Pipeline bridge
from runtime.pipeline_bridge import init_bridge

# P2-3: Bearer token auth for API endpoints
from runtime.auth import verify_api_key

# Fix-C: Wire knowledge-inject (P2.7) + P2.5 context monitors into HOOK_REGISTRY
# and ALWAYS_ON_HOOKS at import time. Must precede any SkillRouter instantiation.
import runtime.init_hooks  # noqa: F401  (side-effect: registers knowledge-inject)


def configure_logger(name: str, level: str) -> logging.Logger:
    """Configure a stdout logger that emits JSON strings."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def emit_log(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a structured log line."""
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, sort_keys=True))


@dataclass
class RuntimeState:
    """Mutable runtime state stored on the FastAPI app."""

    settings: RuntimeSettings
    router: SkillRouter | None = None
    skill_index: dict[str, dict[str, Any]] = field(default_factory=dict)
    startup_error: str | None = None
    draining: bool = False  # AUDIT-FIX: P1-1 -- graceful shutdown flag

    def provider_status(self) -> dict[str, dict[str, Any]]:
        if not self.router:
            return {}
        return self.router.get_status()

    def missing_required_providers(self) -> list[str]:
        pstatus = self.provider_status()
        missing = []
        for provider in self.settings.required_providers:
            info = pstatus.get(provider)
            if not info or not info.get("connected"):
                missing.append(provider)
        return missing

    def readiness_payload(self) -> dict[str, Any]:
        missing = self.missing_required_providers()
        ready = not self.startup_error and not missing and bool(self.skill_index)
        # AUDIT-FIX: P1-11 -- return minimal info on 200; full detail on 503
        if ready:
            return {"status": "ready"}
        return {
            "status": "not_ready",
            "missing_required_providers": missing,
            "startup_error": self.startup_error,
        }

    def is_ready(self) -> bool:
        payload = self.readiness_payload()
        return payload["status"] == "ready"


def load_skill_index(router: SkillRouter) -> dict[str, dict[str, Any]]:
    """Load all canonical skill definitions to catch broken files before traffic."""
    skill_index: dict[str, dict[str, Any]] = {}

    for skill_dir in sorted(router_path for router_path in router_path_iter(router)):
        skill_id = skill_dir.name
        loaded = router.load_skill(skill_id)
        skill_index[skill_id] = {
            "config": loaded["config"],
            "schema": loaded["schema"],
        }
    if not skill_index:
        raise RuntimeError("No skills found under skills/")
    return skill_index


def router_path_iter(router: SkillRouter):
    """Return canonical skill directories from the repo skills/ folder."""
    if hasattr(router, "skill_map") and router.skill_map:
        return sorted(router.skill_map.values())

    from pathlib import Path
    skill_root = getattr(router, "skill_root", None) or Path("skills")
    return (p.parent for p in sorted(skill_root.rglob("skill.yaml")))


def create_app(
    settings: RuntimeSettings | None = None,
    router_factory: Callable[[str], SkillRouter] = SkillRouter,
    inventory_factory: Callable[[SkillRouter], dict[str, dict[str, Any]]] = load_skill_index,
) -> FastAPI:
    """Create the private operator runtime app."""

    runtime_settings = settings or RuntimeSettings.from_env()
    logger = configure_logger("audhd_agents.runtime", runtime_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = RuntimeState(settings=runtime_settings)
        try:
            router = router_factory(runtime_settings.config_path)
            state.router = router
            state.skill_index = inventory_factory(router)

            # P2-2: Initialize pipeline bridge so webhook handlers can
            # dispatch events to the cognitive pipeline
            init_bridge(router, state.skill_index)

            emit_log(
                logger,
                "runtime_startup_complete",
                app_env=runtime_settings.app_env,
                required_providers=list(runtime_settings.required_providers),
                skill_count=len(state.skill_index),
                pipeline_bridge="initialized",
            )
        except Exception as exc:  # pragma: no cover - exercised via readyz tests
            state.startup_error = str(exc)
            emit_log(
                logger,
                "runtime_startup_failed",
                app_env=runtime_settings.app_env,
                error=str(exc),
            )

        app.state.runtime = state
        app.state.logger = logger
        yield

        # AUDIT-FIX: P1-1 -- graceful shutdown: drain in-flight requests
        state.draining = True
        default_grace = 10
        raw_grace = os.environ.get("SHUTDOWN_GRACE_SECONDS")
        grace = default_grace
        if raw_grace is not None:
            try:
                parsed = int(raw_grace)
                # Clamp to a sane range: no negative sleep
                grace = max(parsed, 0)
            except (TypeError, ValueError):
                emit_log(
                    logger,
                    "shutdown_grace_seconds_invalid",
                    value=raw_grace,
                    default_seconds=default_grace,
                )
        emit_log(logger, "shutdown_draining", grace_seconds=grace)
        await asyncio.sleep(grace)

    app = FastAPI(
        title=runtime_settings.service_name,
        version="2.1.0",
        description="AuDHD Cognitive Swarm runtime with webhook-to-skill pipeline",
        lifespan=lifespan,
    )
    app.state.runtime = RuntimeState(
        settings=runtime_settings,
        startup_error="runtime startup not completed",
    )
    app.state.logger = logger

    # P2-1: Register middleware stack (CORS, request ID, logging, timing)
    register_middleware(app)

    # P2-1: Mount webhook router
    app.include_router(webhook_router)

    def get_state(request: Request) -> RuntimeState:
        return request.app.state.runtime

    @app.get("/healthz")
    async def healthz(request: Request):
        state = get_state(request)
        return {
            "service": state.settings.service_name,
            "app_env": state.settings.app_env,
            "status": "ok",
        }

    @app.get("/readyz")
    async def readyz(request: Request):
        state = get_state(request)
        payload = state.readiness_payload()
        if payload["status"] != "ready":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=payload,
            )
        return payload

    @app.post("/execute", response_model=ExecuteResponse, dependencies=[Depends(verify_api_key)])
    async def execute(request: Request, payload: ExecuteRequest):
        state = get_state(request)
        logger = request.app.state.logger

        # AUDIT-FIX: P1-1 -- reject new requests during graceful shutdown
        if state.draining:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service shutting down",
            )

        # P1-1: Crash mode short-circuit
        # PROFILE.md contract: crash = save state, stop. No model call.
        if payload.cognitive_state.is_crash():
            emit_log(
                logger,
                "crash_mode_activated",
                request_id=payload.request_id,
                skill_id=payload.skill_id,
            )
            return ExecuteResponse(
                output={},
                model_used=None,
                provider=None,
                energy_level=EnergyLevel.CRASH,
                request_id=payload.request_id,
                latency_ms=0,
                crash_state=CrashStateResponse(
                    checkpoint=f"skill:{payload.skill_id}:input_received",
                    resume_action=(
                        f"Re-run skill '{payload.skill_id}' "
                        f"at low or medium energy when ready."
                    ),
                ),
                cognitive_compliance=CognitiveCompliance(compliant=True),
            )

        readiness = state.readiness_payload()
        if readiness["status"] != "ready":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=readiness,
            )

        skill_id_provided = bool(payload.skill_id)

        if skill_id_provided and payload.skill_id not in state.skill_index:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown skill_id: {payload.skill_id}",
            )

        request_id = payload.request_id
        started_at = time.time()

        try:
            # Sanitize input before passing to router
            cleaned_text, injection_patterns = sanitize_input(payload.input_text)
            if injection_patterns:
                emit_log(
                    logger,
                    "injection_patterns_detected",
                    request_id=request_id,
                    skill_id=payload.skill_id,
                    patterns=injection_patterns,
                )

            skill_request = SkillRequest(
                skill_id=payload.skill_id,
                input_text=cleaned_text,
                options=payload.options,
                model_override=payload.model_override,
            )
            if skill_id_provided:
                result = await state.router.execute(  # type: ignore[union-attr]
                    skill_request,
                    cognitive_state_override=payload.cognitive_state,  # P1-1
                )
            else:
                result = await state.router.execute_chain(  # type: ignore[union-attr]
                    skill_request,
                    cognitive_state_override=payload.cognitive_state,
                )
        except Exception as exc:
            emit_log(
                logger,
                "skill_execution_failed",
                request_id=request_id,
                skill_id=payload.skill_id or "capability-chain",
                model_override=payload.model_override,
                latency_ms=int((time.time() - started_at) * 1000),
                failure_class=exc.__class__.__name__,
                error=str(exc),
            )
            # AUDIT-FIX: P1-4-early -- never leak internal details to client
            logger.exception("Skill execution failed", exc_info=exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Skill execution failed",
            ) from exc

        emit_log(
            logger,
            "skill_execution_succeeded",
            request_id=request_id,
            skill_id=payload.skill_id or "capability-chain",
            provider=result.provider,
            model_used=result.model_used,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            cached=result.cached,
        )

        return ExecuteResponse(
            output=result.output,
            model_used=result.model_used,
            provider=result.provider,
            energy_level=payload.cognitive_state.energy_level,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            cached=result.cached,
            request_id=request_id,
            hooks_executed=getattr(result, "hooks_executed", []),
            cognitive_compliance=CognitiveCompliance(compliant=True),
        )

    return app


app = create_app()
