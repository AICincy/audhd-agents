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


# ---------------------------------------------------------------------------
# JSON extraction resilience tests
# ---------------------------------------------------------------------------

class JSONExtractionAdapter:
    """Adapter stub that returns configurable content for JSON extraction tests."""

    circuit_breaker = StubCircuitBreaker()

    def __init__(self, content: str):
        self._content = content

    @staticmethod
    def build_system_prompt(skill_prompt: str, profile_md: str) -> str:
        return f"{profile_md}\n{skill_prompt}"

    async def execute(self, **kwargs):
        return {
            "content": self._content,
            "input_tokens": 10,
            "output_tokens": 10,
            "latency_ms": 5,
        }


def _make_router_with_content(content: str):
    """Helper that builds a SkillRouter with a stub adapter returning `content`."""
    router = SkillRouter.__new__(SkillRouter)
    router.alias_map = {"TEST": "google/gemini-test"}
    adapter = JSONExtractionAdapter(content)
    router.adapters = {"google": adapter}
    router.load_skill = lambda skill_id: {
        "config": {"models": {"primary": "TEST", "fallback": []}},
        "prompt": "Return JSON.",
        "schema": {},
    }
    router.load_profile_md = lambda: "PROFILE"
    return router


def test_json_extraction_clean_markdown():
    """Strategy 1: JSON inside ```json ... ``` block."""
    content = '```json\n{"status": "ok", "value": 42}\n```'
    router = _make_router_with_content(content)
    resp = asyncio.run(router.execute(SkillRequest(skill_id="demo", input_text="hi")))
    output = dict(resp.output)
    output.pop("_validation", None)
    assert output["status"] == "ok"
    assert output["value"] == 42


def test_json_extraction_conversational_preamble():
    """Strategy 2 fallback: Conversational text before bare JSON (no markdown)."""
    content = 'Here is my analysis:\n\n{"finding": "critical", "count": 3}\n\nLet me know if you need more.'
    router = _make_router_with_content(content)
    resp = asyncio.run(router.execute(SkillRequest(skill_id="demo", input_text="hi")))
    output = dict(resp.output)
    output.pop("_validation", None)
    assert output["finding"] == "critical"


def test_json_extraction_no_wrappers():
    """Strategy 2: Bare JSON with no markdown wrappers at all."""
    content = '{"result": "success"}'
    router = _make_router_with_content(content)
    resp = asyncio.run(router.execute(SkillRequest(skill_id="demo", input_text="hi")))
    output = dict(resp.output)
    output.pop("_validation", None)
    assert output["result"] == "success"


def test_json_extraction_mixed_conversation():
    """Strategy 2: LLM wraps response in conversation but JSON is extractable."""
    content = 'I analyzed the code and found:\n{"risk": "high", "issues": ["a", "b"]}\nThose are the main issues.'
    router = _make_router_with_content(content)
    resp = asyncio.run(router.execute(SkillRequest(skill_id="demo", input_text="hi")))
    output = dict(resp.output)
    output.pop("_validation", None)
    assert output["risk"] == "high"
    assert output["issues"] == ["a", "b"]


def test_json_extraction_nested_braces():
    """Strategy 1: Deeply nested JSON inside markdown blocks."""
    content = '```json\n{"outer": {"inner": {"deep": true}}}\n```'
    router = _make_router_with_content(content)
    resp = asyncio.run(router.execute(SkillRequest(skill_id="demo", input_text="hi")))
    output = dict(resp.output)
    output.pop("_validation", None)
    assert output["outer"]["inner"]["deep"] is True


def test_json_extraction_trailing_text_after_markdown():
    """Strategy 1: Markdown block followed by conversational text."""
    content = '```json\n{"done": true}\n```\n\nHope that helps!'
    router = _make_router_with_content(content)
    resp = asyncio.run(router.execute(SkillRequest(skill_id="demo", input_text="hi")))
    output = dict(resp.output)
    output.pop("_validation", None)
    assert output["done"] is True


def test_json_extraction_array_response():
    """Strategy 2: Array JSON response without markdown."""
    content = 'Results:\n[{"id": 1}, {"id": 2}]\nEnd.'
    router = _make_router_with_content(content)
    resp = asyncio.run(router.execute(SkillRequest(skill_id="demo", input_text="hi")))
    output = resp.output
    assert isinstance(output, list)
    assert output[0]["id"] == 1


def test_json_extraction_garbage_input():
    """Strategy 3 fallback: Non-JSON text returns raw content."""
    content = 'This is just plain text with no JSON at all.'
    router = _make_router_with_content(content)
    resp = asyncio.run(router.execute(SkillRequest(skill_id="demo", input_text="hi")))
    output = dict(resp.output)
    output.pop("_validation", None)
    assert "raw" in output
    assert "plain text" in output["raw"]

