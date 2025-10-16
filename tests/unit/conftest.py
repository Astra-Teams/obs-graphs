"""Unit test specific fixtures."""

import pytest


class _BlockedHttpClient:  # pragma: no cover - constructor raises immediately
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "HTTP clients are blocked in unit tests; inject a stub client instead."
        )


@pytest.fixture(autouse=True)
def set_unit_test_env(monkeypatch):
    """Setup environment variables for unit tests.

    Note: Monkeypatch only works for in-process execution.
    For subprocess-based tests, use subprocess env parameter.
    """
    monkeypatch.setenv("OBS_GLX_USE_SQLITE", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_STL_CONN", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_REDIS", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_STARPROBE", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_GITHUB", "true")

    try:
        monkeypatch.setattr(
            "obs_graphs_sdk.workflow_client.client.httpx.Client",
            _BlockedHttpClient,
            raising=True,
        )
    except ModuleNotFoundError:
        # Allow unit tests to proceed when the SDK extra is not installed.
        pass
