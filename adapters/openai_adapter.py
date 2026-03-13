"""OpenAI adapter with async client."""

import os
import time
from typing import Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from .base import BaseAdapter


class OpenAIAdapter(BaseAdapter):
    """Adapter for OpenAI models (GPT-5.x, GPT-5 Codex, GPT Max, o4-mini)."""

    def __init__(self, api_key: Optional[str] = None, config: dict = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        super().__init__(api_key=api_key, config=config or {})
        if AsyncOpenAI:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None

    async def execute(self, model: str, system_prompt: str,
                      user_prompt: str, **kwargs) -> dict:
        if not self.client:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker open for OpenAI")

        start = time.time()
        try:
            create_kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_completion_tokens": kwargs.get("max_tokens", 16384),
                "temperature": kwargs.get("temperature", 0.0),
            }
            if kwargs.get("response_format"):
                create_kwargs["response_format"] = kwargs["response_format"]

            response = await self.client.chat.completions.create(**create_kwargs)
            self.circuit_breaker.record_success()
            latency = int((time.time() - start) * 1000)
            choice = response.choices[0]
            return {
                "content": choice.message.content,
                "model": response.model,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
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
        input_rate = rates.get("cost_per_1k_input", 0.010)
        output_rate = rates.get("cost_per_1k_output", 0.030)
        return (input_tokens / 1000 * input_rate) + \
               (output_tokens / 1000 * output_rate)
