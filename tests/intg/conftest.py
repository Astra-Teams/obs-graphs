import pytest

from dev.mocks_clients.mock_github_client import MockGithubClient
from dev.mocks_clients.mock_ollama_client import MockOllamaClient
from dev.mocks_clients.mock_redis_client import MockRedisClient


@pytest.fixture(autouse=True)
def set_intg_test_env(monkeypatch):
    """Setup environment variables for integration tests - all mocked."""
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("USE_MOCK_GITHUB", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK_REDIS", "true")
    monkeypatch.setenv("USE_MOCK_OLLAMA_DEEP_RESEARCHER", "true")


@pytest.fixture
def mock_github_client() -> MockGithubClient:
    """Provide a mock GitHub client for unit tests."""

    return MockGithubClient()


@pytest.fixture
def mock_ollama_client() -> MockOllamaClient:
    """Provide a mock Ollama client for unit tests."""

    return MockOllamaClient()


@pytest.fixture
def mock_redis_client() -> MockRedisClient:
    """Provide a mock Redis client for unit tests."""

    return MockRedisClient()
