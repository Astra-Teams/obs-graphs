from unittest.mock import MagicMock, patch

import pytest

from src.container import DependencyContainer, get_container


@pytest.fixture
def container():
    return DependencyContainer()


@patch("src.container.get_settings")
@patch("src.container.GithubClient")
def test_get_github_client_lazy_instantiation(
    mock_github_client, mock_get_settings, container: DependencyContainer
):
    mock_settings = MagicMock()
    mock_settings.USE_MOCK_GITHUB = False
    mock_get_settings.return_value = mock_settings
    mock_instance = MagicMock()
    mock_github_client.return_value = mock_instance

    client1 = container.get_github_client()
    client2 = container.get_github_client()

    assert client1 is client2
    assert client1 is mock_instance
    mock_github_client.assert_called_once()


@patch("src.container.get_settings")
def test_get_github_client_returns_mock_when_flag_enabled(
    mock_get_settings, container: DependencyContainer
):
    mock_settings = MagicMock()
    mock_settings.USE_MOCK_GITHUB = True
    mock_get_settings.return_value = mock_settings

    client1 = container.get_github_client()
    client2 = container.get_github_client()

    from dev.mocks_clients import MockGithubClient

    assert isinstance(client1, MockGithubClient)
    assert client1 is client2


@patch("src.container.VaultService")
def test_get_vault_service_lazy_instantiation(
    mock_vault_service, container: DependencyContainer
):
    mock_instance = MagicMock()
    mock_vault_service.return_value = mock_instance

    service1 = container.get_vault_service()
    service2 = container.get_vault_service()

    assert service1 is service2
    assert service1 is mock_instance
    mock_vault_service.assert_called_once()


@patch("src.container.get_settings")
@patch("src.container.OllamaClient")
def test_get_ollama_client_lazy_instantiation(
    mock_ollama_client, mock_get_settings, container: DependencyContainer
):
    mock_settings = MagicMock()
    mock_settings.USE_MOCK_LLM = False
    mock_settings.OLLAMA_MODEL = "llama"
    mock_settings.OLLAMA_BASE_URL = "http://localhost"
    mock_get_settings.return_value = mock_settings
    mock_instance = MagicMock()
    mock_ollama_client.return_value = mock_instance

    client1 = container.get_ollama_client()
    client2 = container.get_ollama_client()

    assert client1 is client2
    assert client1 is mock_instance
    mock_ollama_client.assert_called_once_with(
        model="llama", base_url="http://localhost"
    )


@patch("src.container.get_settings")
def test_get_ollama_client_returns_mock_when_flag_enabled(
    mock_get_settings, container: DependencyContainer
):
    mock_settings = MagicMock()
    mock_settings.USE_MOCK_LLM = True
    mock_get_settings.return_value = mock_settings

    client1 = container.get_ollama_client()
    client2 = container.get_ollama_client()

    from dev.mocks_clients import MockOllamaClient

    assert client1 is client2
    assert isinstance(client1, MockOllamaClient)


def test_get_node_valid_name(container: DependencyContainer):
    node = container.get_node("select_category")
    assert node is container.get_node("select_category")


def test_get_node_invalid_name(container: DependencyContainer):
    with pytest.raises(ValueError, match="Unknown node: invalid_node"):
        container.get_node("invalid_node")


def test_get_container_singleton():
    container1 = get_container()
    container2 = get_container()

    assert container1 is container2
    assert isinstance(container1, DependencyContainer)
