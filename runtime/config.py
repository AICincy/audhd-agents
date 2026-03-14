"""Environment parsing for the private runtime service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


VALID_APP_ENVS = {"staging", "production"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
DEFAULT_REQUIRED_PROVIDERS = ("google",)


@dataclass(frozen=True)
class RuntimeSettings:
    """Runtime configuration derived from environment variables."""

    app_env: str
    log_level: str
    required_providers: tuple[str, ...]
    config_path: str = "adapters/config.yaml"
    skills_dir: Path = Path("skills")
    service_name: str = "audhd-agents-runtime"

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        app_env = (os.getenv("APP_ENV") or "staging").strip().lower()
        if app_env not in VALID_APP_ENVS:
            raise ValueError(
                f"APP_ENV must be one of {sorted(VALID_APP_ENVS)}, got: {app_env!r}"
            )

        log_level = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
        if log_level not in VALID_LOG_LEVELS:
            raise ValueError(
                f"LOG_LEVEL must be one of {sorted(VALID_LOG_LEVELS)}, got: {log_level!r}"
            )

        raw_required = os.getenv(
            "REQUIRED_PROVIDERS", ",".join(DEFAULT_REQUIRED_PROVIDERS)
        )
        required_providers = tuple(
            provider.strip().lower()
            for provider in raw_required.split(",")
            if provider.strip()
        )
        if not required_providers:
            required_providers = DEFAULT_REQUIRED_PROVIDERS

        return cls(
            app_env=app_env,
            log_level=log_level,
            required_providers=required_providers,
        )
