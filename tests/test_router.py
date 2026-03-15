"""Router and provider selection unit tests."""

from __future__ import annotations

import asyncio

from adapters.base import SkillRequest
from adapters.google_adapter import GoogleAdapter
from adapters.router import SkillRouter


class StubCircuitBreaker:
    """Always-open circuit breaker stub."""

    @staticmethod
    def can_execute():
        return True


class FailingAdapter:
    """Adapter stub that always fails."""

    circuit_breaker = StubCircuitBreaker()

    @staticmethod
    def build_system_prompt(skill_prompt: str, profile_md: str) -> str:
        return f"{profile_md}\n{skill_prompt}"

    async def execute(self, **kwargs):
        raise RuntimeError("primary failed")


class SuccessfulAdapter:
    """Adapter stub that succeeds with a fixed payload."""

    circuit_breaker = StubCircuitBreaker()

    @staticmethod
    def build_system_prompt(skill_prompt: str, profile_md: str) -> str:
        return f"{profile_md}\n{skill_prompt}"

    async def execute(self, **kwargs):
        return {
            "content": '{"status":"ok"}',
            "input_tokens": 12,
            "output_tokens": 5,
            "latency_ms": 17,
        }


def test_resolve_alias_returns_provider_and_model():
    router = SkillRouter.__new__(SkillRouter)
    router.alias_map = {"O-54": "openai/gpt-5.4"}

    provider, model = router.resolve_alias("O-54")

    assert provider == "openai"
    assert model == "gpt-5.4"


def test_execute_fails_over_to_fallback_model():
    router = SkillRouter.__new__(SkillRouter)
    router.alias_map = {
        "PRIMARY": "openai/gpt-5.4",
        "FALLBACK": "google/gemini-2.5-pro",
    }
    router.adapters = {
        "openai": FailingAdapter(),
        "google": SuccessfulAdapter(),
    }
    router.load_skill = lambda skill_id: {
        "config": {"models": {"primary": "PRIMARY", "fallback": ["FALLBACK"]}},
        "prompt": "Return JSON.",
        "schema": {},
    }
    router.load_profile_md = lambda: "PROFILE"

    response = asyncio.run(
        router.execute(SkillRequest(skill_id="demo", input_text="hello"))
    )

    assert response.provider == "google"
    assert response.model_used == "gemini-2.5-pro"
    output = dict(response.output)
    output.pop("_validation", None)
    assert output == {"status": "ok"}


def test_google_adapter_prefers_vertex_when_vertex_key_present(monkeypatch):
    adapter = GoogleAdapter.__new__(GoogleAdapter)
    adapter.config = {
        "vertex_mode_env": "GOOGLE_GENAI_USE_VERTEXAI",
        "vertex_api_key_env": "VERTEX_API_KEY",
        "vertex_service_account_env": "VERTEX_SERVICE_ACCOUNT",
        "vertex_service_account_file_env": "VERTEX_SERVICE_ACCOUNT_FILE",
        "google_application_credentials_env": "GOOGLE_APPLICATION_CREDENTIALS",
    }

    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.setenv("VERTEX_API_KEY", "vertex-test-key")

    assert adapter._should_use_vertex() is True
