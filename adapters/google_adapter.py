"""Google (Gemini) adapter with native async."""

import os
import time
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from .base import BaseAdapter


class GoogleAdapter(BaseAdapter):
    """Adapter for Google Gemini models."""

    def __init__(self, api_key: Optional[str] = None, config: dict = None):
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        super().__init__(api_key=api_key, config=config or {})
        if genai:
            genai.configure(api_key=self.api_key)

    async def execute(self, model: str, system_prompt: str,
                      user_prompt: str, **kwargs) -> dict:
        if not genai:
            raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker open for Google")

        start = time.time()
        try:
            gen_model = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=kwargs.get("temperature", 0.0),
                    max_output_tokens=kwargs.get("max_tokens", 65536),
                ),
            )
            response = await gen_model.generate_content_async(user_prompt)
            self.circuit_breaker.record_success()
            latency = int((time.time() - start) * 1000)

            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

            return {
                "content": response.text,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency,
            }
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise

    def build_system_prompt(self, skill_prompt: str, krass_md: str) -> str:
        return f"{krass_md}\n\n---\n\n{skill_prompt}"

    def estimate_cost(self, input_tokens: int,
                      output_tokens: int, model: str) -> float:
        rates = self.config.get("models", {}).get(model, {})
        input_rate = rates.get("cost_per_1k_input", 0.00125)
        output_rate = rates.get("cost_per_1k_output", 0.005)
        return (input_tokens / 1000 * input_rate) + \
               (output_tokens / 1000 * output_rate)
