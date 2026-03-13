"""Anthropic (Claude) adapter with async client."""

import os
import time
from typing import Optional

try:
    import anthropic
except ImportError:
    anthropic = None

from .base import BaseAdapter


class AnthropicAdapter(BaseAdapter):
    """Adapter for Anthropic Claude models (Opus, Sonnet)."""

    def __init__(self, api_key: Optional[str] = None, config: dict = None):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        super().__init__(api_key=api_key, config=config or {})
        if anthropic:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None

    async def execute(self, model: str, system_prompt: str,
                      user_prompt: str, **kwargs) -> dict:
        if not self.client:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker open for Anthropic")

        start = time.time()
        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=kwargs.get("max_tokens", 16000),
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=kwargs.get("temperature", 0.0),
            )
            self.circuit_breaker.record_success()
            latency = int((time.time() - start) * 1000)
            return {
                "content": response.content[0].text,
                "model": response.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "latency_ms": latency,
            }
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise

    def build_system_prompt(self, skill_prompt: str, profile_md: str) -> str:
        return f"{profile_md}\n\n---\n\n{skill_prompt}"

    def estimate_cost(self, input_tokens: int,
                      output_tokens: int, model: str) -> float:
        rates = self.config.get("models", {}).get(model, {})
        input_rate = rates.get("cost_per_1k_input", 0.015)
        output_rate = rates.get("cost_per_1k_output", 0.075)
        return (input_tokens / 1000 * input_rate) + \
               (output_tokens / 1000 * output_rate)
