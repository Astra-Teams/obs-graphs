import pytest

from dev.mocks_clients.mock_github_client import MockGithubClient
from dev.mocks_clients.mock_ollama_client import MockOllamaClient
from dev.mocks_clients.mock_redis_client import MockRedisClient


@pytest.fixture
def mock_settings(default_settings):
    """Provide settings with mocks for unit tests."""

    settings_with_mocks = default_settings.model_copy(
        update={
            "use_mock_github": True,
            "use_mock_llm": True,
            "use_mock_redis": True,
            "use_mock_research_api": True,
        }
    )

    # Ensure global settings reference is updated for code paths that access it directly
    from src import settings as settings_module

    original_settings = settings_module.settings
    settings_module.settings = settings_with_mocks

    try:
        yield settings_with_mocks
    finally:
        settings_module.settings = original_settings


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
