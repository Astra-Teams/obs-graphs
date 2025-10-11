"""Unit tests for the DependencyContainer."""

from unittest.mock import MagicMock, patch

import pytest

from src.obs_graphs.container import DependencyContainer, get_container


@pytest.fixture
def container():
    """Return a fresh DependencyContainer instance."""
    return DependencyContainer()


@patch("src.obs_graphs.container.obs_graphs_settings")
def test_get_github_client_returns_mock_when_flag_enabled(
    mock_obs_settings, container: DependencyContainer, default_settings
):
    """Test that MockGithubClient is returned when USE_MOCK_GITHUB=True."""
    mock_obs_settings.use_mock_github = True
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


@patch("src.obs_graphs.container.obs_graphs_settings")
def test_get_llm_returns_mock_when_flag_enabled(
    mock_obs_settings, container: DependencyContainer, default_settings
):
    """Test that MockOllamaClient is returned when USE_MOCK_LLM=True."""
    mock_obs_settings.use_mock_llm = True
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


def test_get_container_singleton():
    """Test that get_container returns the same instance."""
    # Act
    container1 = get_container()
    container2 = get_container()

    # Assert
    assert container1 is container2
    assert isinstance(container1, DependencyContainer)


@patch("src.obs_graphs.container.obs_graphs_settings")
def test_get_redis_client_returns_mock_when_flag_enabled(
    mock_obs_settings, container: DependencyContainer, default_settings
):
    """Test that FakeRedis is returned when USE_MOCK_REDIS=True."""
    mock_obs_settings.use_mock_redis = True
    # Act
    client1 = container.get_redis_client()
    client2 = container.get_redis_client()

    # Assert
    import fakeredis

    assert isinstance(client1, fakeredis.FakeRedis)
    assert client1 is client2  # Should be cached
