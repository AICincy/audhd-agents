"""Base adapter interface for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import time
import json


@dataclass
class SkillRequest:
    """Incoming skill execution request."""
    skill_id: str
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
    cost: float = 0.0
    latency_ms: int = 0
    cached: bool = False


@dataclass
class CostRecord:
    """Cost tracking record."""
    timestamp: str
    skill_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: int


class CircuitBreaker:
    """Circuit breaker for provider failover."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        return True  # half-open: allow one request


class BaseAdapter(ABC):
    """Base adapter all providers must implement."""

    def __init__(self, api_key: str, config: dict):
        self.api_key = api_key
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.get("failure_threshold", 3),
            recovery_timeout=config.get("recovery_timeout", 60),
        )

    @abstractmethod
    async def execute(self, model: str, system_prompt: str,
                      user_prompt: str, **kwargs) -> dict:
        """Execute a prompt against the provider."""
        ...

    @abstractmethod
    def build_system_prompt(self, skill_prompt: str,
                            krass_md: str) -> str:
        """Build provider-specific system prompt from skill prompt + KRASS.md."""
        ...

    @abstractmethod
    def estimate_cost(self, input_tokens: int,
                      output_tokens: int, model: str) -> float:
        """Estimate cost for a request."""
        ...

    def log_cost(self, record: CostRecord, log_file: str = "logs/cost.jsonl"):
        """Append cost record to JSONL log."""
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "a") as f:
            f.write(json.dumps(record.__dict__) + "\n")
