"""Unit tests for the dependency injection system."""

import pytest
from obs_gtwy_sdk import MockObsGatewayClient

from src.obs_graphs import dependencies
from src.obs_graphs.clients import OllamaClient
from src.obs_graphs.config import (
    GatewaySettings,
    MLXSettings,
    ObsGraphsSettings,
    OllamaSettings,
)


class TestConfigurationProviders:
    """Test configuration provider functions."""

    def test_get_app_settings(self):
        """Test that get_app_settings returns ObsGraphsSettings."""
        settings = dependencies.get_app_settings()
        assert isinstance(settings, ObsGraphsSettings)

    def test_get_ollama_settings(self):
        """Test that get_ollama_settings returns OllamaSettings."""
        settings = dependencies.get_ollama_settings()
        assert isinstance(settings, OllamaSettings)

    def test_get_mlx_settings(self):
        """Test that get_mlx_settings returns MLXSettings."""
        settings = dependencies.get_mlx_settings()
        assert isinstance(settings, MLXSettings)

    def test_get_gateway_settings(self):
        """Test that get_gateway_settings returns GatewaySettings."""
        settings = dependencies.get_gateway_settings()
        assert isinstance(settings, GatewaySettings)

    def test_settings_are_cached(self):
        """Test that settings providers use lru_cache and return same instance."""
        settings1 = dependencies.get_app_settings()
        settings2 = dependencies.get_app_settings()
        assert settings1 is settings2


class TestLLMClientFactory:
    """Test LLM client factory and provider functions."""

    def test_get_llm_client_ollama(self, monkeypatch):
        """Test that get_llm_client returns OllamaClient when backend is ollama."""
        monkeypatch.setenv("OBS_GRAPHS_LLM_BACKEND", "ollama")
        monkeypatch.setenv("OBS_GRAPHS_USE_MOCK_LLM", "false")

        # Clear cache to pick up new env vars
        dependencies.get_app_settings.cache_clear()
        dependencies.get_ollama_settings.cache_clear()
        dependencies.get_mlx_settings.cache_clear()

        # Call with actual settings, not Depends
        client = dependencies.get_llm_client(
            settings=dependencies.get_app_settings(),
            ollama_settings=dependencies.get_ollama_settings(),
            mlx_settings=dependencies.get_mlx_settings(),
        )
        assert isinstance(client, OllamaClient)

    def test_get_llm_client_mock(self, monkeypatch):
        """Test that get_llm_client returns mock client when USE_MOCK_LLM is true."""
        monkeypatch.setenv("OBS_GRAPHS_USE_MOCK_LLM", "true")
        monkeypatch.setenv("OBS_GRAPHS_LLM_BACKEND", "ollama")

        # Clear cache to pick up new env vars
        dependencies.get_app_settings.cache_clear()
        dependencies.get_ollama_settings.cache_clear()
        dependencies.get_mlx_settings.cache_clear()

        client = dependencies.get_llm_client(
            settings=dependencies.get_app_settings(),
            ollama_settings=dependencies.get_ollama_settings(),
            mlx_settings=dependencies.get_mlx_settings(),
        )
        assert isinstance(client, OllamaClient)
        # Mock client should be wrapped in OllamaClient

    def test_get_llm_client_invalid_backend(self, monkeypatch):
        """Test that invalid backend is caught by settings validation."""
        # The validation happens at settings level, not at get_llm_client level
        # So we expect a ValidationError from Pydantic
        from pydantic_core import ValidationError

        monkeypatch.setenv("OBS_GRAPHS_LLM_BACKEND", "invalid_backend")
        monkeypatch.setenv("OBS_GRAPHS_USE_MOCK_LLM", "false")

        # Clear cache to pick up new env vars
        dependencies.get_app_settings.cache_clear()

        with pytest.raises(ValidationError):
            dependencies.get_app_settings()

    def test_get_llm_client_provider(self):
        """Test that get_llm_client_provider returns a callable."""
        provider = dependencies.get_llm_client_provider(
            settings=dependencies.get_app_settings(),
            ollama_settings=dependencies.get_ollama_settings(),
            mlx_settings=dependencies.get_mlx_settings(),
        )
        assert callable(provider)

    def test_llm_client_provider_returns_client(self, monkeypatch):
        """Test that the provider function returns an LLM client."""
        monkeypatch.setenv("OBS_GRAPHS_LLM_BACKEND", "ollama")
        monkeypatch.setenv("OBS_GRAPHS_USE_MOCK_LLM", "false")

        # Clear cache
        dependencies.get_app_settings.cache_clear()
        dependencies.get_ollama_settings.cache_clear()
        dependencies.get_mlx_settings.cache_clear()

        provider = dependencies.get_llm_client_provider(
            settings=dependencies.get_app_settings(),
            ollama_settings=dependencies.get_ollama_settings(),
            mlx_settings=dependencies.get_mlx_settings(),
        )
        client = provider()
        # Check that it's an Ollama client (concrete type check instead of protocol)
        assert isinstance(client, OllamaClient)

    def test_llm_client_provider_with_backend_override(self, monkeypatch):
        """Test that provider accepts backend parameter to override default."""
        monkeypatch.setenv("OBS_GRAPHS_LLM_BACKEND", "ollama")
        monkeypatch.setenv("OBS_GRAPHS_USE_MOCK_LLM", "false")

        # Clear cache
        dependencies.get_app_settings.cache_clear()
        dependencies.get_ollama_settings.cache_clear()
        dependencies.get_mlx_settings.cache_clear()

        provider = dependencies.get_llm_client_provider(
            settings=dependencies.get_app_settings(),
            ollama_settings=dependencies.get_ollama_settings(),
            mlx_settings=dependencies.get_mlx_settings(),
        )

        # Request ollama explicitly
        client = provider("ollama")
        assert isinstance(client, OllamaClient)


class TestServiceProviders:
    """Test service provider functions."""

    def test_get_vault_service(self, monkeypatch):
        """Test that get_vault_service returns VaultServiceProtocol."""
        # Set vault path
        monkeypatch.setenv("OBS_GRAPHS_VAULT_SUBMODULE_PATH", "/tmp/test_vault")

        # Clear cache
        dependencies.get_app_settings.cache_clear()

        vault_service = dependencies.get_vault_service(
            settings=dependencies.get_app_settings()
        )
        assert vault_service is not None
        # VaultService should have the protocol methods

    def test_get_gateway_client(self, monkeypatch):
        """Test that get_gateway_client returns appropriate client."""
        monkeypatch.setenv("OBS_GRAPHS_USE_MOCK_OBS_GATEWAY", "true")

        # Clear cache
        dependencies.get_app_settings.cache_clear()
        dependencies.get_gateway_settings.cache_clear()

        client = dependencies.get_gateway_client(
            settings=dependencies.get_app_settings(),
            gateway_settings=dependencies.get_gateway_settings(),
        )
        assert client is not None
        assert isinstance(client, MockObsGatewayClient)

    def test_get_research_client(self, monkeypatch):
        """Test that get_research_client returns appropriate client."""
        monkeypatch.setenv("OBS_GRAPHS_USE_MOCK_OLLAMA_DEEP_RESEARCHER", "true")

        # Clear cache
        dependencies.get_app_settings.cache_clear()
        dependencies.get_research_api_settings.cache_clear()

        client = dependencies.get_research_client(
            settings=dependencies.get_app_settings(),
            research_settings=dependencies.get_research_api_settings(),
        )
        assert client is not None

    def test_get_redis_client(self, monkeypatch):
        """Test that get_redis_client returns appropriate client."""
        monkeypatch.setenv("OBS_GRAPHS_USE_MOCK_REDIS", "true")

        # Clear cache
        dependencies.get_app_settings.cache_clear()
        dependencies.get_redis_settings.cache_clear()

        client = dependencies.get_redis_client(
            settings=dependencies.get_app_settings(),
            redis_settings=dependencies.get_redis_settings(),
        )
        assert client is not None
