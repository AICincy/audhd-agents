"""Shared fixtures for the test suite.

Sets AUDHD_API_KEYS so that the fail-secure auth gate (AUDIT-FIX A-1)
allows tests to reach the /execute endpoint.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _set_test_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a test API key is available for all tests."""
    monkeypatch.setenv("AUDHD_API_KEYS", "test-key-1,test-key-2")
