"""Google Gemini adapter for Gemini Developer API and Vertex AI."""

import json
import os
import time
from pathlib import Path
from typing import Optional

from pydantic import SecretStr

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from google.oauth2 import service_account
except ImportError:
    service_account = None

from .base import BaseAdapter

# Shared timeout configuration for Google GenAI.
# google-genai HttpOptions.timeout expects milliseconds.
TIMEOUT_SECONDS = 120
TIMEOUT_MS = TIMEOUT_SECONDS * 1000


class GoogleAdapter(BaseAdapter):
    """Adapter for Gemini via Gemini Developer API or Vertex AI."""

    def __init__(self, api_key: Optional[SecretStr] = None, config: dict = None):
        self.config = config or {}
        self.init_error = None
        self.project = None
        self.location = None
        self.backend = "developer"
        self.auth_mode = "unconfigured"

        raw_dev_key = os.getenv(
            self.config.get("env_key", "GOOGLE_API_KEY")
        )
        developer_api_key = api_key or (SecretStr(raw_dev_key) if raw_dev_key else None)
        raw_vertex_key = os.getenv(
            self.config.get("vertex_api_key_env", "VERTEX_API_KEY")
        )
        self.vertex_api_key = SecretStr(raw_vertex_key) if raw_vertex_key else None
        self.use_vertex = self._should_use_vertex()

        selected_key = self.vertex_api_key if self.use_vertex else developer_api_key
        super().__init__(api_key=selected_key, config=self.config)

        self.client = None
        try:
            self.client = self._build_client(developer_api_key)
        except Exception as exc:
            self.init_error = str(exc)

    async def execute(
        self, model: str, system_prompt: str, user_prompt: str, **kwargs
    ) -> dict:
        if not self.client or not types:
            raise RuntimeError(self.init_error or "Google client not initialized")
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker open for Google")

        start = time.time()
        try:
            thinking_budget = kwargs.get("thinking_budget")
            thinking_config = None
            if thinking_budget is not None and hasattr(types, "ThinkingConfig"):
                thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=kwargs.get("temperature", 0.0),
                max_output_tokens=kwargs.get("max_tokens", 65536),
                thinking_config=thinking_config,
            )
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=user_prompt,
                config=config,
            )
            self.circuit_breaker.record_success()
            latency = int((time.time() - start) * 1000)

            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            output_tokens = (
                (getattr(usage, "candidates_token_count", 0) or 0) if usage else 0
            )

            return {
                "content": self._extract_text(response),
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency,
                "headers": getattr(response, "headers", {}),
            }
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    def build_system_prompt(self, skill_prompt: str, profile_md: str) -> str:
        return f"{profile_md}\n\n---\n\n{skill_prompt}"

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        rates = self.config.get("models", {}).get(model, {})
        input_rate = rates.get("cost_per_1k_input", 0.00125)
        output_rate = rates.get("cost_per_1k_output", 0.005)
        return (input_tokens / 1000 * input_rate) + (output_tokens / 1000 * output_rate)

    @classmethod
    def has_configuration(cls, config: dict) -> bool:
        """Return whether any Google auth surface is configured."""
        cfg = config or {}
        env_names = [
            cfg.get("env_key", "GOOGLE_API_KEY"),
            cfg.get("vertex_mode_env", "GOOGLE_GENAI_USE_VERTEXAI"),
            cfg.get("vertex_api_key_env", "VERTEX_API_KEY"),
            cfg.get("vertex_service_account_env", "VERTEX_SERVICE_ACCOUNT"),
            cfg.get("vertex_service_account_file_env", "VERTEX_SERVICE_ACCOUNT_FILE"),
            cfg.get(
                "google_application_credentials_env",
                "GOOGLE_APPLICATION_CREDENTIALS",
            ),
        ]
        return any(os.getenv(name) for name in env_names)

    def _should_use_vertex(self) -> bool:
        """Decide whether to route Google calls through Vertex AI."""
        mode_env = os.getenv(
            self.config.get("vertex_mode_env", "GOOGLE_GENAI_USE_VERTEXAI")
        )
        if mode_env is not None and mode_env.strip():
            return mode_env.strip().lower() in {"1", "true", "yes", "on"}

        return any(
            os.getenv(name)
            for name in (
                self.config.get("vertex_api_key_env", "VERTEX_API_KEY"),
                self.config.get("vertex_service_account_env", "VERTEX_SERVICE_ACCOUNT"),
                self.config.get(
                    "vertex_service_account_file_env",
                    "VERTEX_SERVICE_ACCOUNT_FILE",
                ),
                self.config.get(
                    "google_application_credentials_env",
                    "GOOGLE_APPLICATION_CREDENTIALS",
                ),
            )
        )

    def _build_client(self, developer_api_key: Optional[SecretStr]):
        """Initialize the google-genai client for the selected backend."""
        if not genai or not types:
            raise RuntimeError(
                "google-genai package not installed. Run: pip install google-genai"
            )

        if self.use_vertex:
            return self._build_vertex_client()

        if not developer_api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY for Gemini Developer API")

        self.backend = "developer"
        self.auth_mode = "api_key"
        http_options = types.HttpOptions(api_version="v1beta", timeout=TIMEOUT_MS)
        return genai.Client(
            api_key=developer_api_key.get_secret_value(),
            http_options=http_options,
        )

    def _build_vertex_client(self):
        """Initialize Vertex AI client using API key or ADC/service account."""
        self.backend = "vertex"

        http_options = types.HttpOptions(api_version="v1", timeout=TIMEOUT_MS)

        if self.vertex_api_key:
            self.auth_mode = "vertex_api_key"
            return genai.Client(
                vertexai=True,
                api_key=self.vertex_api_key.get_secret_value(),
                http_options=http_options,
            )

        credentials = self._load_vertex_credentials()
        self.project = os.getenv(
            self.config.get("vertex_project_env", "GOOGLE_CLOUD_PROJECT")
        ) or os.getenv(self.config.get("project_id_env", "GOOGLE_PROJECT_ID"))
        self.location = os.getenv(
            self.config.get("vertex_location_env", "GOOGLE_CLOUD_LOCATION")
        ) or self.config.get("vertex_default_location", "global")

        if not self.project:
            raise RuntimeError(
                "Vertex AI requires GOOGLE_CLOUD_PROJECT or GOOGLE_PROJECT_ID "
                "when VERTEX_API_KEY is not set"
            )
        if not self.location:
            raise RuntimeError(
                "Vertex AI requires GOOGLE_CLOUD_LOCATION when VERTEX_API_KEY is not set"
            )

        self.auth_mode = "service_account" if credentials else "adc"
        return genai.Client(
            vertexai=True,
            project=self.project,
            location=self.location,
            credentials=credentials,
            http_options=http_options,
        )

    def _load_vertex_credentials(self):
        """Load service-account credentials when configured."""
        if self.vertex_api_key:
            return None

        file_env = os.getenv(
            self.config.get(
                "vertex_service_account_file_env", "VERTEX_SERVICE_ACCOUNT_FILE"
            )
        ) or os.getenv(
            self.config.get(
                "google_application_credentials_env",
                "GOOGLE_APPLICATION_CREDENTIALS",
            )
        )
        inline_env = os.getenv(
            self.config.get("vertex_service_account_env", "VERTEX_SERVICE_ACCOUNT")
        )

        if not file_env and not inline_env:
            return None
        if not service_account:
            raise RuntimeError(
                "google-auth is required for Vertex service-account auth"
            )

        if file_env:
            return service_account.Credentials.from_service_account_file(file_env)

        assert inline_env is not None  # guaranteed by the guard above
        raw_value = inline_env.strip()
        if raw_value.startswith("{"):
            return service_account.Credentials.from_service_account_info(
                json.loads(raw_value)
            )

        if Path(raw_value).exists():
            return service_account.Credentials.from_service_account_file(raw_value)

        raise RuntimeError(
            "VERTEX_SERVICE_ACCOUNT must be a JSON string or a readable file path"
        )

    def _extract_text(self, response) -> str:
        """Return response text even when the SDK convenience accessor is empty."""
        text = getattr(response, "text", None)
        if text:
            return text

        collected = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    collected.append(part_text)
        return "".join(collected)
