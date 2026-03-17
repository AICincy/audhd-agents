"""Base adapter interface for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import threading
import time

from pydantic import SecretStr

# Shared LLM request timeout in seconds. Adapters convert to milliseconds
# where required by their SDK (e.g. Google GenAI HttpOptions.timeout).
LLM_TIMEOUT_SECONDS: int = 120


@dataclass
class SkillRequest:
    """Incoming skill execution request."""

    skill_id: Optional[str]
    input_text: str
    options: dict = field(default_factory=dict)
    model_override: Optional[str] = None


@dataclass
class SkillResponse:
    """Skill execution response."""

    output: dict
    model_used: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    headers: dict = field(default_factory=dict)
    cached: bool = False


@dataclass
class CostRecord:
    """Cost tracking record (optional logging only)."""

    timestamp: str
    skill_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class CircuitBreaker:
    """Circuit breaker for provider failover."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()  # AUDIT-FIX: A-2
        # Track whether a single probe request is currently in-flight in half-open state
        self._half_open_probe_in_flight: bool = False

    def record_failure(self) -> None:
        with self._lock:  # AUDIT-FIX: A-2
            # On failure during half-open, immediately reopen the circuit
            if self.state == "half-open":
                self.failure_count = self.failure_threshold
                self.last_failure_time = time.time()
                self.state = "open"
                self._half_open_probe_in_flight = False
                return
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                # Ensure any stale half-open probe flag is cleared
                self._half_open_probe_in_flight = False

    def record_success(self) -> None:
        with self._lock:  # AUDIT-FIX: A-2
            # On success during half-open, close the circuit again
            if self.state == "half-open":
                self.failure_count = 0
                self.state = "closed"
                self._half_open_probe_in_flight = False
                return
            self.failure_count = 0
            self.state = "closed"
            self._half_open_probe_in_flight = False

    def can_execute(self) -> bool:
        with self._lock:  # AUDIT-FIX: A-2
            if self.state == "closed":
                return True
            if self.state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    # Transition to half-open and allow a single probe request
                    self.state = "half-open"
                else:
                    return False
            if self.state == "half-open":
                # Allow only one in-flight probe request at a time
                if not self._half_open_probe_in_flight:
                    self._half_open_probe_in_flight = True
                    return True
                return False
            return False


class BaseAdapter(ABC):
    """Base adapter all providers must implement."""

    def __init__(self, api_key: Optional[SecretStr], config: dict):
        self._api_key = api_key
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.get("failure_threshold", 3),
            recovery_timeout=config.get("recovery_timeout", 60),
        )

    @property
    def api_key(self) -> str:
        """Return the raw API key string. Use only when passing to SDK clients."""
        key = self._api_key
        if key is None:
            return ""
        return key.get_secret_value()

    @abstractmethod
    async def execute(
        self, model: str, system_prompt: str, user_prompt: str, **kwargs
    ) -> dict:
        """Execute a prompt against the provider."""
        ...

    @abstractmethod
    def build_system_prompt(self, skill_prompt: str, profile_md: str) -> str:
        """Build provider-specific system prompt from skill prompt + PROFILE.md."""
        ...
