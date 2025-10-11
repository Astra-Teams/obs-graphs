"""Unit test specific fixtures."""

import pytest


@pytest.fixture(autouse=True)
def set_unit_test_env(monkeypatch):
    """Setup environment variables for unit tests.

    Note: Monkeypatch only works for in-process execution.
    For subprocess-based tests, use subprocess env parameter.
    """
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("USE_MOCK_GITHUB", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK_REDIS", "true")
    monkeypatch.setenv("USE_MOCK_OLLAMA_DEEP_RESEARCHER", "true")
