"""Runtime endpoint tests for the private operator API."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from adapters.base import SkillResponse
from runtime.app import create_app
from runtime.config import RuntimeSettings


@dataclass
class FakeRouter:
    """Minimal router double for runtime tests."""

    status_payload: dict
    response_payload: SkillResponse | None = None

    def get_status(self):
        return self.status_payload

    async def execute(self, request, cognitive_state_override=None):
        if self.response_payload is None:
            raise RuntimeError("no response configured")
        return self.response_payload


def make_settings(required_providers=("openai",)):
    """Return runtime settings for tests."""
    return RuntimeSettings(
        app_env="staging",
        log_level="INFO",
        required_providers=tuple(required_providers),
    )


def make_client(status_payload, skill_index=None, response_payload=None, required_providers=("openai",)):
    """Create a test client around a fake runtime router."""
    fake_router = FakeRouter(
        status_payload=status_payload,
        response_payload=response_payload,
    )
    app = create_app(
        settings=make_settings(required_providers),
        router_factory=lambda _: fake_router,
        inventory_factory=lambda _: skill_index or {"demo-skill": {"config": {}, "schema": {}}},
    )
    return TestClient(app)


def test_healthz_returns_process_status():
    with make_client(
        status_payload={"openai": {"connected": True}},
        response_payload=SkillResponse(
            output={"status": "ok"},
            model_used="gpt-5.4",
            provider="openai",
        ),
    ) as client:
        response = client.get("/healthz")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_readyz_fails_when_required_provider_missing():
    with make_client(
        status_payload={"openai": {"connected": True}},
        required_providers=("openai", "anthropic"),
        response_payload=SkillResponse(
            output={"status": "ok"},
            model_used="gpt-5.4",
            provider="openai",
        ),
    ) as client:
        response = client.get("/readyz")

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["status"] == "not_ready"
        assert detail["missing_required_providers"] == ["anthropic"]


def test_execute_returns_structured_response():
    with make_client(
        status_payload={"openai": {"connected": True}},
        response_payload=SkillResponse(
            output={"raw": "done"},
            model_used="gpt-5.4",
            provider="openai",
            input_tokens=10,
            output_tokens=4,
            latency_ms=25,
        ),
    ) as client:
        response = client.post(
            "/execute",
            json={
                "skill_id": "demo-skill",
                "input_text": "run the demo",
                "request_id": "req-123",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["provider"] == "openai"
        assert body["model_used"] == "gpt-5.4"
        assert body["request_id"] == "req-123"


def test_execute_rejects_unknown_skill():
    with make_client(
        status_payload={"openai": {"connected": True}},
        response_payload=SkillResponse(
            output={"raw": "done"},
            model_used="gpt-5.4",
            provider="openai",
        ),
    ) as client:
        response = client.post(
            "/execute",
            json={"skill_id": "missing-skill", "input_text": "run it"},
        )

        assert response.status_code == 404
        assert "Unknown skill_id" in response.json()["detail"]


def test_execute_validates_required_fields():
    with make_client(
        status_payload={"openai": {"connected": True}},
        response_payload=SkillResponse(
            output={"raw": "done"},
            model_used="gpt-5.4",
            provider="openai",
        ),
    ) as client:
        response = client.post("/execute", json={"skill_id": "demo-skill"})

        assert response.status_code == 422
