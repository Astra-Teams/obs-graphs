"""Unit tests for the DependencyContainer."""

from unittest.mock import MagicMock, patch

import pytest

from src.container import DependencyContainer, get_container


@pytest.fixture
def container():
    """Return a fresh DependencyContainer instance."""
    return DependencyContainer()


@patch("src.container.GithubClient")
def test_get_github_client_lazy_instantiation(
    mock_github_client, container: DependencyContainer
):
    """Test that github client is lazily instantiated."""
    # Arrange
    mock_instance = MagicMock()
    mock_github_client.return_value = mock_instance

    # Act
    client1 = container.get_github_client()
    client2 = container.get_github_client()

    # Assert
    assert client1 is client2
    assert client1 is mock_instance
    mock_github_client.assert_called_once()


@patch("src.container.VaultService")
def test_get_vault_service_lazy_instantiation(
    mock_vault_service, container: DependencyContainer
):
    """Test that vault service is lazily instantiated."""
    # Arrange
    mock_instance = MagicMock()
    mock_vault_service.return_value = mock_instance

    # Act
    service1 = container.get_vault_service()
    service2 = container.get_vault_service()

    # Assert
    assert service1 is service2
    assert service1 is mock_instance
    mock_vault_service.assert_called_once()


@patch("src.container.get_settings")
@patch("src.container.Ollama")
def test_get_llm_lazy_instantiation(
    mock_ollama, mock_get_settings, container: DependencyContainer
):
    """Test that LLM is lazily instantiated."""
    # Arrange
    mock_settings = MagicMock()
    mock_settings.OLLAMA_MODEL = "test-model"
    mock_settings.OLLAMA_BASE_URL = "http://test-url"
    mock_get_settings.return_value = mock_settings
    mock_instance = MagicMock()
    mock_ollama.return_value = mock_instance

    # Act
    llm1 = container.get_llm()
    llm2 = container.get_llm()

    # Assert
    assert llm1 is llm2
    assert llm1 is mock_instance
    mock_ollama.assert_called_once_with(model="test-model", base_url="http://test-url")


def test_get_node_valid_name(container: DependencyContainer):
    """Test getting a node with a valid name."""
    # Act
    node = container.get_node("article_improvement")

    # Assert
    assert node is not None
    # Should be cached
    node2 = container.get_node("article_improvement")
    assert node is node2


def test_get_node_invalid_name(container: DependencyContainer):
    """Test getting a node with an invalid name raises ValueError."""
    # Act & Assert
    with pytest.raises(ValueError, match="Unknown node: invalid_node"):
        container.get_node("invalid_node")


@patch("src.container.get_settings")
@patch("src.container.Ollama")
def test_get_node_new_article_creation_with_llm(
    mock_ollama, mock_get_settings, container: DependencyContainer
):
    """Test that new_article_creation node is instantiated with LLM."""
    # Arrange
    mock_settings = MagicMock()
    mock_settings.OLLAMA_MODEL = "test-model"
    mock_settings.OLLAMA_BASE_URL = "http://test-url"
    mock_get_settings.return_value = mock_settings
    mock_llm = MagicMock()
    mock_ollama.return_value = mock_llm

    # Act
    node = container.get_node("new_article_creation")

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
