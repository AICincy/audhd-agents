"""Private FastAPI runtime for operator-driven skill execution.

P1-1: Added cognitive_state to /execute request schema.
- Import ExecuteRequest/ExecuteResponse from runtime.schemas
- Crash mode short-circuit (no model call when energy=crash)
- cognitive_state passthrough to router
- Backward compatible: omitting cognitive_state defaults to medium/focused/new
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status

from adapters.base import SkillRequest
from adapters.router import SkillRouter
from runtime.config import RuntimeSettings

# P1-1: Cognitive state schemas
from runtime.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    CrashStateResponse,
    CognitiveCompliance,
    EnergyLevel,
)


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
        return {
            "service": self.settings.service_name,
            "app_env": self.settings.app_env,
            "status": "ready" if ready else "not_ready",
            "required_providers": list(self.settings.required_providers),
            "missing_required_providers": missing,
            "skill_count": len(self.skill_index),
            "startup_error": self.startup_error,
            "providers": self.provider_status(),
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
            emit_log(
                logger,
                "runtime_startup_complete",
                app_env=runtime_settings.app_env,
                required_providers=list(runtime_settings.required_providers),
                skill_count=len(state.skill_index),
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

    app = FastAPI(
        title=runtime_settings.service_name,
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.runtime = RuntimeState(
        settings=runtime_settings,
        startup_error="runtime startup not completed",
    )
    app.state.logger = logger

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

    @app.post("/execute", response_model=ExecuteResponse)
    async def execute(request: Request, payload: ExecuteRequest):
        state = get_state(request)
        logger = request.app.state.logger

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

        if payload.skill_id not in state.skill_index:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown skill_id: {payload.skill_id}",
            )

        request_id = payload.request_id
        started_at = time.time()

        try:
            result = await state.router.execute(  # type: ignore[union-attr]
                SkillRequest(
                    skill_id=payload.skill_id,
                    input_text=payload.input_text,
                    options=payload.options,
                    model_override=payload.model_override,
                ),
                cognitive_state_override=payload.cognitive_state,  # P1-1
            )
        except Exception as exc:
            emit_log(
                logger,
                "skill_execution_failed",
                request_id=request_id,
                skill_id=payload.skill_id,
                model_override=payload.model_override,
                latency_ms=int((time.time() - started_at) * 1000),
                failure_class=exc.__class__.__name__,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        emit_log(
            logger,
            "skill_execution_succeeded",
            request_id=request_id,
            skill_id=payload.skill_id,
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
