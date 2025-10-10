"""Unit tests for the DependencyContainer."""

from unittest.mock import MagicMock, patch

import pytest

from src.obs_graphs.container import DependencyContainer, get_container


@pytest.fixture
def container():
    """Return a fresh DependencyContainer instance."""
    return DependencyContainer()


@patch("src.obs_graphs.container.settings")
@patch("src.obs_graphs.container.GithubClient")
def test_get_github_client_lazy_instantiation(
    mock_github_client,
    mock_settings,
    container: DependencyContainer,
    default_settings,
):
    """Test that github client is lazily instantiated."""
    # Arrange
    mock_settings.configure_mock(**default_settings.model_dump())
    mock_instance = MagicMock()
    mock_github_client.return_value = mock_instance

    # Act
    client1 = container.get_github_client()
    client2 = container.get_github_client()

    # Assert
    assert client1 is client2
    assert client1 is mock_instance
    mock_github_client.assert_called_once()


@patch("src.obs_graphs.container.settings")
def test_get_github_client_returns_mock_when_flag_enabled(
    mock_settings, container: DependencyContainer, default_settings
):
    """Test that MockGithubClient is returned when USE_MOCK_GITHUB=True."""
    # Arrange
    mock_settings.configure_mock(**default_settings.model_dump())

    # Act
    client1 = container.get_github_client()
    client2 = container.get_github_client()

    # Assert
    from dev.mocks_clients import MockGithubClient

    assert isinstance(client1, MockGithubClient)
    assert client1 is client2  # Should be cached


@patch("src.obs_graphs.container.VaultService")
def test_get_vault_service_lazy_instantiation(
    mock_vault_service, container: DependencyContainer, tmp_path
):
    """Test that vault service is lazily instantiated."""
    # Arrange
    container.set_vault_path(tmp_path)
    mock_instance = MagicMock()
    mock_vault_service.return_value = mock_instance

    # Act
    service1 = container.get_vault_service()
    service2 = container.get_vault_service()

    # Assert
    assert service1 is service2
    assert service1 is mock_instance
    mock_vault_service.assert_called_once_with(tmp_path)


@patch("src.obs_graphs.container.settings")
@patch("src.obs_graphs.container.OllamaLLM")
def test_get_llm_lazy_instantiation(
    mock_ollama, mock_settings, container: DependencyContainer, default_settings
):
    """Test that LLM is lazily instantiated."""
    # Arrange
    mock_settings.configure_mock(**default_settings.model_dump())
    mock_settings.llm_model = "test-model"
    mock_settings.ollama_host = "http://test-url"
    mock_instance = MagicMock()
    mock_ollama.return_value = mock_instance

    # Act
    llm1 = container.get_llm()
    llm2 = container.get_llm()

    # Assert
    assert llm1 is llm2
    assert llm1 is mock_instance
    mock_ollama.assert_called_once_with(model="test-model", base_url="http://test-url")


@patch("src.obs_graphs.container.settings")
def test_get_llm_returns_mock_when_flag_enabled(
    mock_settings, container: DependencyContainer, default_settings
):
    """Test that MockOllamaClient is returned when USE_MOCK_LLM=True."""
    # Arrange
    mock_settings.configure_mock(**default_settings.model_dump())

    # Act
    llm1 = container.get_llm()
    llm2 = container.get_llm()

    # Assert
    from dev.mocks_clients import MockOllamaClient

    assert isinstance(llm1, MockOllamaClient)
    assert llm1 is llm2  # Should be cached


@patch("src.obs_graphs.container.GithubService")
def test_get_github_service_lazy_instantiation(
    mock_github_service, container: DependencyContainer
):
    """Test that GithubService is lazily instantiated and cached."""
    mock_instance = MagicMock()
    mock_github_service.return_value = mock_instance
    container.get_github_client = MagicMock(return_value=MagicMock())

    service1 = container.get_github_service()
    service2 = container.get_github_service()

    assert service1 is service2 is mock_instance
    mock_github_service.assert_called_once()


def test_get_node_valid_name(container: DependencyContainer):
    """Test getting a node with a valid name."""
    # Act
    node = container.get_node("article_proposal")

    # Assert
    assert node is not None
    # Should be cached
    node2 = container.get_node("article_proposal")
    assert node is node2


def test_get_node_invalid_name(container: DependencyContainer):
    """Test getting a node with an invalid name raises ValueError."""
    # Act & Assert
    with pytest.raises(ValueError, match="Unknown node: invalid_node"):
        container.get_node("invalid_node")


@patch("src.obs_graphs.container.settings")
@patch("src.obs_graphs.container.OllamaLLM")
def test_get_node_new_article_creation_with_llm(
    mock_ollama,
    mock_settings,
    container: DependencyContainer,
    default_settings,
):
    """Test that article_proposal node is instantiated with LLM."""
    # Arrange
    mock_settings.configure_mock(**default_settings.model_dump())
    mock_settings.llm_model = "test-model"
    mock_settings.ollama_host = "http://test-url"
    mock_llm = MagicMock()
    mock_ollama.return_value = mock_llm

    # Act
    node = container.get_node("article_proposal")

    # Assert
    assert node is not None
    # Verify that get_llm was called (since it's lazy, it should be called during get_node)
    mock_ollama.assert_called_once_with(model="test-model", base_url="http://test-url")


def test_get_container_singleton():
    """Test that get_container returns the same instance."""
    # Act
    container1 = get_container()
    container2 = get_container()

    # Assert
    assert container1 is container2
    assert isinstance(container1, DependencyContainer)


@patch("src.obs_graphs.container.settings")
@patch("src.obs_graphs.container.redis.Redis")
def test_get_redis_client_production_mode(
    mock_redis,
    mock_settings,
    container: DependencyContainer,
    default_settings,
):
    """Test that redis.Redis is returned when USE_MOCK_REDIS=False."""
    # Arrange
    mock_settings.configure_mock(**default_settings.model_dump())
    # Mock the redis_settings as an object with celery_broker_url attribute
    mock_redis_settings = MagicMock()
    mock_redis_settings.celery_broker_url = "redis://localhost:6379/0"
    mock_settings.redis_settings = mock_redis_settings
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


@patch("src.obs_graphs.container.settings")
def test_get_redis_client_returns_mock_when_flag_enabled(
    mock_settings, container: DependencyContainer, default_settings
):
    """Test that FakeRedis is returned when USE_MOCK_REDIS=True."""
    # Arrange
    mock_settings.configure_mock(**default_settings.model_dump())

    # Act
    client1 = container.get_redis_client()
    client2 = container.get_redis_client()

    # Assert
    import fakeredis

    assert isinstance(client1, fakeredis.FakeRedis)
    assert client1 is client2  # Should be cached
