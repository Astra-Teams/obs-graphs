"""SDK test fixtures ensuring isolation from production services."""

import pytest


@pytest.fixture(autouse=True)
def configure_sdk_test_env(monkeypatch):
    """Force SDK tests to operate entirely with mocks."""

    monkeypatch.setenv("OBS_GLX_USE_SQLITE", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_STL_CONN", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_REDIS", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_STARPROBE", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_NEXUS", "true")

    class _BlockedHttpClient:  # pragma: no cover - constructor raises immediately
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "HTTP clients are blocked in SDK tests; inject a stub client instead."
            )

    try:
        monkeypatch.setattr(
            "obs_graphs_sdk.workflow_client.client.httpx.Client",
            _BlockedHttpClient,
        )
    except ModuleNotFoundError as exc:  # pragma: no cover - explicit failure path
        raise RuntimeError(
            "obs_graphs_sdk is not available. Install the SDK extra before running SDK tests."
        ) from exc
