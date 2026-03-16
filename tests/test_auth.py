"""Tests for authentication middleware.

Covers:
- API key verification
- Bearer token extraction
- Missing auth handling
- Dev mode (no keys configured)
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from runtime.auth import get_api_keys, get_webhook_secret


class TestGetWebhookSecret:
    def test_reads_from_env(self):
        with patch.dict(os.environ, {"NOTION_WEBHOOK_SECRET": "mysecret"}):
            assert get_webhook_secret() == "mysecret"

    def test_raises_when_missing(self):
        with patch.dict(
            os.environ, {"NOTION_WEBHOOK_SECRET": ""}, clear=False
        ):
            with pytest.raises(ValueError, match="NOTION_WEBHOOK_SECRET"):
                get_webhook_secret()

    def test_strips_whitespace(self):
        with patch.dict(
            os.environ, {"NOTION_WEBHOOK_SECRET": "  secret  "}
        ):
            assert get_webhook_secret() == "secret"


class TestGetApiKeys:
    def test_reads_comma_separated(self):
        with patch.dict(os.environ, {"AUDHD_API_KEYS": "key1,key2,key3"}):
            keys = get_api_keys()
            assert keys == {"key1", "key2", "key3"}

    def test_empty_returns_empty_set(self):
        with patch.dict(
            os.environ, {"AUDHD_API_KEYS": ""}, clear=False
        ):
            assert get_api_keys() == set()

    def test_strips_whitespace(self):
        with patch.dict(
            os.environ, {"AUDHD_API_KEYS": " key1 , key2 "}
        ):
            assert get_api_keys() == {"key1", "key2"}

    def test_missing_env_returns_empty(self):
        env = os.environ.copy()
        env.pop("AUDHD_API_KEYS", None)
        with patch.dict(os.environ, env, clear=True):
            assert get_api_keys() == set()
