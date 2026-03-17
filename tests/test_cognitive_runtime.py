"""tests/test_cognitive_runtime.py

P1-1 validation gate: cognitive_state in /execute.

Tests:
  1. /execute accepts full cognitive_state
  2. /execute defaults cognitive_state when omitted (backward compat)
  3. Crash mode short-circuits with no model call
  4. Crash mode returns CrashStateResponse shape
  5. Energy level echoed in response
  6. Request ID auto-generated when omitted
  7. Request ID preserved when provided
  8. Invalid energy level rejected (422)
  9. /healthz unaffected by cognitive changes
  10. /readyz unaffected by cognitive changes
  11. Hooks executed list returned
  12. Resume context flows through

Run: pytest tests/test_cognitive_runtime.py -v
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from adapters.base import SkillResponse
from runtime.app import create_app
from runtime.config import RuntimeSettings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@dataclass
class CognitiveCapturingRouter:
    """Fake router that captures cognitive_state_override for assertions."""

    status_payload: dict
    response_payload: SkillResponse | None = None
    last_request: object = None
    last_cognitive_state: object = None
    execute_called: bool = False

    def get_status(self):
        return self.status_payload

    async def execute(self, request, cognitive_state_override=None):
        self.execute_called = True
        self.last_request = request
        self.last_cognitive_state = cognitive_state_override
        if self.response_payload is None:
            raise RuntimeError("no response configured")
        return self.response_payload


def make_settings():
    return RuntimeSettings(
        app_env="staging",
        log_level="INFO",
        required_providers=("openai",),
    )


def make_client(router):
    app = create_app(
        settings=make_settings(),
        router_factory=lambda _: router,
        inventory_factory=lambda _: {
            "engineering-code-reviewer": {"config": {}, "schema": {}},
            "testing-accessibility-auditor": {"config": {}, "schema": {}},
            "project-manager-senior": {"config": {}, "schema": {}},
        },
    )
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer test-key-1"
    return client


def default_router(**kwargs):
    return CognitiveCapturingRouter(
        status_payload={"openai": {"connected": True}},
        response_payload=SkillResponse(
            output={
                "verdict": "Test passed.",
                "confidence": 0.95,
                "single_next_action": "Proceed.",
                "parking_lot": [],
            },
            model_used="gpt-5.4",
            provider="openai",
            input_tokens=150,
            output_tokens=50,
            latency_ms=25,
        ),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Test 1: Full cognitive_state accepted
# ---------------------------------------------------------------------------

def test_execute_accepts_full_cognitive_state():
    """P1-1 core: /execute accepts cognitive_state in request body."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "engineering-code-reviewer",
            "input_text": "Review this function.",
            "cognitive_state": {
                "energy_level": "high",
                "attention_state": "focused",
                "session_context": "new",
                "resume_from": None,
            },
        })

        assert response.status_code == 200
        data = response.json()
        assert data["energy_level"] == "high"
        assert data["model_used"] == "gpt-5.4"
        assert data["provider"] == "openai"
        assert router.execute_called
        assert router.last_cognitive_state is not None
        assert router.last_cognitive_state.energy_level.value == "high"


# ---------------------------------------------------------------------------
# Test 2: Defaults when cognitive_state omitted (backward compat)
# ---------------------------------------------------------------------------

def test_execute_defaults_cognitive_state_when_omitted():
    """Backward compatibility: omitting cognitive_state uses sensible defaults."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "engineering-code-reviewer",
            "input_text": "Review this function.",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["energy_level"] == "medium"
        assert router.last_cognitive_state is not None
        cs = router.last_cognitive_state
        assert cs.energy_level.value == "medium"
        assert cs.attention_state.value == "focused"
        assert cs.session_context.value == "new"


# ---------------------------------------------------------------------------
# Test 3: Crash mode short-circuits (no model call)
# ---------------------------------------------------------------------------

def test_crash_mode_no_model_call():
    """PROFILE.md contract: crash = save state, stop. No model call."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "engineering-code-reviewer",
            "input_text": "Review this function.",
            "cognitive_state": {
                "energy_level": "crash",
            },
        })

        assert response.status_code == 200
        assert not router.execute_called


# ---------------------------------------------------------------------------
# Test 4: Crash mode returns CrashStateResponse shape
# ---------------------------------------------------------------------------

def test_crash_mode_response_shape():
    """Crash mode returns checkpoint, resume_action, message."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "testing-accessibility-auditor",
            "input_text": "Audit this page.",
            "cognitive_state": {
                "energy_level": "crash",
            },
        })

        data = response.json()
        assert data["energy_level"] == "crash"
        assert data["model_used"] is None
        assert data["provider"] is None
        assert data["output"] == {}

        crash = data["crash_state"]
        assert crash is not None
        assert "checkpoint" in crash
        assert "resume_action" in crash
        assert crash["message"] == "Checkpoint saved. One action when ready."
        assert "testing-accessibility-auditor" in crash["checkpoint"]

        assert data["cognitive_compliance"]["compliant"] is True
        assert data["cognitive_compliance"]["violations"] == []


# ---------------------------------------------------------------------------
# Test 5: Energy level echoed in response
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("energy", ["high", "medium", "low"])
def test_energy_level_echoed_in_response(energy):
    """Response echoes the energy level used for routing."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "engineering-code-reviewer",
            "input_text": "Test.",
            "cognitive_state": {"energy_level": energy},
        })

        assert response.status_code == 200
        assert response.json()["energy_level"] == energy


# ---------------------------------------------------------------------------
# Test 6: Request ID auto-generated
# ---------------------------------------------------------------------------

def test_request_id_auto_generated():
    """request_id is auto-generated UUID when not provided."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "engineering-code-reviewer",
            "input_text": "Test.",
        })

        data = response.json()
        assert data["request_id"] != ""
        assert len(data["request_id"]) == 36  # UUID format


# ---------------------------------------------------------------------------
# Test 7: Request ID preserved when provided
# ---------------------------------------------------------------------------

def test_request_id_preserved():
    """Provided request_id flows through to response."""
    router = default_router()
    with make_client(router) as client:
        custom_id = "my-custom-request-123"
        response = client.post("/execute", json={
            "skill_id": "engineering-code-reviewer",
            "input_text": "Test.",
            "request_id": custom_id,
        })

        assert response.json()["request_id"] == custom_id


# ---------------------------------------------------------------------------
# Test 8: Invalid energy level rejected
# ---------------------------------------------------------------------------

def test_invalid_energy_level_rejected():
    """Pydantic rejects invalid energy_level values."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "engineering-code-reviewer",
            "input_text": "Test.",
            "cognitive_state": {"energy_level": "turbo"},
        })

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 9: /healthz unaffected
# ---------------------------------------------------------------------------

def test_healthz_unaffected():
    """/healthz works exactly as before. No cognitive changes."""
    router = default_router()
    with make_client(router) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Test 10: /readyz unaffected
# ---------------------------------------------------------------------------

def test_readyz_unaffected():
    """/readyz works exactly as before. No cognitive changes."""
    router = default_router()
    with make_client(router) as client:
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


# ---------------------------------------------------------------------------
# Test 11: Hooks executed list returned
# ---------------------------------------------------------------------------

def test_hooks_executed_returned():
    """Response includes hooks_executed field."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "engineering-code-reviewer",
            "input_text": "Test.",
        })

        data = response.json()
        assert "hooks_executed" in data
        assert data["hooks_executed"] == []


# ---------------------------------------------------------------------------
# Test 12: Resume context flows through
# ---------------------------------------------------------------------------

def test_resume_context_flows_through():
    """Where Was I: resumed session with checkpoint passes to router."""
    router = default_router()
    with make_client(router) as client:
        response = client.post("/execute", json={
            "skill_id": "project-manager-senior",
            "input_text": "Continue planning.",
            "cognitive_state": {
                "energy_level": "low",
                "session_context": "resumed",
                "resume_from": "checkpoint-abc-123",
            },
        })

        assert response.status_code == 200
        cs = router.last_cognitive_state
        assert cs.session_context.value == "resumed"
        assert cs.resume_from == "checkpoint-abc-123"
        assert cs.needs_resume() is True
