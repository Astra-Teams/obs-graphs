import pytest

from dev.mocks.clients.mock_redis_client import MockRedisClient


@pytest.fixture(autouse=True)
def set_intg_test_env(monkeypatch):
    """Setup environment variables for integration tests - all mocked."""
    monkeypatch.setenv("OBS_GLX_USE_SQLITE", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_STL_CONN", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_REDIS", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_STARPROBE", "true")
    monkeypatch.setenv("OBS_GLX_USE_MOCK_GITHUB", "true")


@pytest.fixture
def mock_redis_client() -> MockRedisClient:
    """Provide a mock Redis client for unit tests."""

    return MockRedisClient()
