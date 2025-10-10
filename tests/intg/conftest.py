import pytest

from dev.mocks_clients.mock_github_client import MockGithubClient
from dev.mocks_clients.mock_ollama_client import MockOllamaClient
from dev.mocks_clients.mock_redis_client import MockRedisClient
from tests.envs import setup_intg_test_env


@pytest.fixture(autouse=True)
def set_intg_test_env(monkeypatch):
    """Setup environment variables for integration tests."""
    setup_intg_test_env(monkeypatch)


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
