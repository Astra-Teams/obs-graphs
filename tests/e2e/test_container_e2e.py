"""E2E tests for DependencyContainer lazy instantiation with real services."""

from unittest.mock import MagicMock, patch

import pytest

from src.obs_graphs.container import DependencyContainer


@pytest.fixture
def container():
    """Return a fresh DependencyContainer instance."""
    return DependencyContainer()


@patch("src.obs_graphs.container.gateway_settings")
@patch("src.obs_graphs.container.ObsGatewayClient")
@patch("src.obs_graphs.container.obs_graphs_settings")
def test_get_gateway_client_production_mode(
    mock_obs_settings,
    mock_obs_gateway_client,
    mock_gateway_settings,
    container: DependencyContainer,
):
    """Gateway client should instantiate the real HTTP client when mocks are disabled."""
    mock_obs_settings.use_mock_obs_gateway = False
    mock_gateway_settings.base_url = "http://gateway"
    mock_gateway_settings.timeout_seconds = 12.5
    mock_instance = MagicMock()
    mock_obs_gateway_client.return_value = mock_instance

    client1 = container.get_gateway_client()
    client2 = container.get_gateway_client()

    assert client1 is client2 is mock_instance
    mock_obs_gateway_client.assert_called_once_with(
        base_url="http://gateway",
        timeout_seconds=12.5,
    )


@patch("src.obs_graphs.container.ollama_settings")
@patch("src.obs_graphs.container.OllamaClient")
@patch("src.obs_graphs.container.obs_graphs_settings")
def test_get_llm_lazy_instantiation(
    mock_obs_settings,
    mock_ollama_client,
    mock_ollama_settings,
    container: DependencyContainer,
):
    """Test that LLM is lazily instantiated."""
    # Arrange
    mock_obs_settings.use_mock_llm = False
    mock_obs_settings.llm_backend = "ollama"
    mock_ollama_settings.model = "test-model"
    mock_ollama_settings.base_url = "http://test-url/"
    mock_instance = MagicMock()
    mock_ollama_client.return_value = mock_instance

    # Act
    llm1 = container.get_llm()
    llm2 = container.get_llm()

    # Assert
    assert llm1 is llm2
    assert llm1 is mock_instance
    mock_ollama_client.assert_called_once_with(
        model="test-model",
        base_url="http://test-url/",
    )


@patch("src.obs_graphs.container.obs_graphs_settings")
@patch("src.obs_graphs.container.redis_settings")
@patch("src.obs_graphs.container.redis.Redis")
def test_get_redis_client_production_mode(
    mock_redis,
    mock_redis_settings,
    mock_obs_settings,
    container: DependencyContainer,
):
    """Test that redis.Redis is returned when USE_MOCK_REDIS=False."""
    # Arrange
    mock_obs_settings.use_mock_redis = False
    # Mock the redis_settings as an object with celery_broker_url attribute
    mock_redis_settings.celery_broker_url = "redis://localhost:6379/0"
    mock_instance = MagicMock()
    mock_redis.from_url.return_value = mock_instance

    # Act
    client1 = container.get_redis_client()
    client2 = container.get_redis_client()

    # Assert
    assert client1 is client2  # Should be cached
    assert client1 is mock_instance
    mock_redis.from_url.assert_called_once_with(
        "redis://localhost:6379/0", decode_responses=True
    )


@patch("src.obs_graphs.container.obs_graphs_settings")
def test_get_node_new_article_creation_with_llm(
    mock_obs_settings,
    container: DependencyContainer,
):
    """Test that article_proposal node obtains LLM client via provider during execution."""
    # Arrange
    mock_obs_settings.use_mock_llm = False
    mock_obs_settings.llm_backend = "ollama"
    mock_llm_client = MagicMock()
    mock_llm_client.invoke.return_value = """
    {
        "title": "Sample Topic",
        "summary": "Sample summary",
        "tags": ["tag1", "tag2"],
        "slug": "sample-topic"
    }
    """
    container.provide_llm_client = MagicMock(return_value=mock_llm_client)

    # Act
    node = container.get_node("article_proposal")
    result = node.execute(
        {"prompt": ["Test prompt"], "strategy": "research_proposal"}
    )

    # Assert
    assert result.success is True
    container.provide_llm_client.assert_called_once_with(None)
