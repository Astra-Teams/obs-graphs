"""Unit tests for the dependency injection system."""

from obs_gtwy_sdk import MockObsGatewayClient
from stl_conn_sdk.stl_conn_client import MockStlConnClient, StlConnClient

from src.obs_graphs import dependencies
from src.obs_graphs.config import (
    GatewaySettings,
    ObsGraphsSettings,
    StlConnSettings,
)


class TestConfigurationProviders:
    """Test configuration provider functions."""

    def test_get_app_settings(self):
        """Test that get_app_settings returns ObsGraphsSettings."""
        settings = dependencies.get_app_settings()
        assert isinstance(settings, ObsGraphsSettings)

    def test_get_stl_conn_settings(self):
        """Test that get_stl_conn_settings returns StlConnSettings."""
        settings = dependencies.get_stl_conn_settings()
        assert isinstance(settings, StlConnSettings)

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

    def test_get_llm_client_mock(self, monkeypatch):
        """Test that get_llm_client returns MockStlConnClient when mock is enabled."""
        monkeypatch.setenv("USE_MOCK_STL_CONN", "true")

        # Clear cache to pick up new env vars
        dependencies.get_stl_conn_settings.cache_clear()

        client = dependencies.get_llm_client(
            stl_conn_settings=dependencies.get_stl_conn_settings(),
        )
        assert isinstance(client, MockStlConnClient)

    def test_get_llm_client_real(self, monkeypatch):
        """Test that get_llm_client returns StlConnClient when mock is disabled."""
        monkeypatch.setenv("USE_MOCK_STL_CONN", "false")

        # Clear cache to pick up new env vars
        dependencies.get_stl_conn_settings.cache_clear()

        client = dependencies.get_llm_client(
            stl_conn_settings=dependencies.get_stl_conn_settings(),
        )
        assert isinstance(client, StlConnClient)

    def test_get_llm_client_provider(self):
        """Test that get_llm_client_provider returns a callable."""
        provider = dependencies.get_llm_client_provider(
            stl_conn_settings=dependencies.get_stl_conn_settings(),
        )
        assert callable(provider)

    def test_llm_client_provider_returns_client(self, monkeypatch):
        """Test that the provider function returns an LLM client."""
        monkeypatch.setenv("USE_MOCK_STL_CONN", "true")

        # Clear cache
        dependencies.get_stl_conn_settings.cache_clear()

        provider = dependencies.get_llm_client_provider(
            stl_conn_settings=dependencies.get_stl_conn_settings(),
        )
        client = provider()
        assert isinstance(client, MockStlConnClient)

    def test_llm_client_provider_ignores_backend_parameter(self, monkeypatch):
        """Test that provider ignores backend parameter (for API compatibility)."""
        monkeypatch.setenv("USE_MOCK_STL_CONN", "true")

        # Clear cache
        dependencies.get_stl_conn_settings.cache_clear()

        provider = dependencies.get_llm_client_provider(
            stl_conn_settings=dependencies.get_stl_conn_settings(),
        )

        # Request different backends - should all return same client type
        client1 = provider("ollama")
        client2 = provider("mlx")
        client3 = provider(None)

        assert isinstance(client1, MockStlConnClient)
        assert isinstance(client2, MockStlConnClient)
        assert isinstance(client3, MockStlConnClient)


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
