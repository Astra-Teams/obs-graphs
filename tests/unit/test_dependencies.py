"""Unit tests for the dependency injection system."""

from nexus_sdk.nexus_client import MockNexusClient, NexusClient
from pytest import MonkeyPatch

from src.obs_glx import dependencies
from src.obs_glx.config import (
    GitHubSettings,
    NexusSettings,
    ObsGlxSettings,
)
from src.obs_glx.services.github_draft_service import MockGitHubDraftService


class TestConfigurationProviders:
    """Test configuration provider functions."""

    def test_get_app_settings(self):
        """Test that get_app_settings returns ObsGraphsSettings."""
        settings = dependencies.get_app_settings()
        assert isinstance(settings, ObsGlxSettings)

    def test_get_nexus_settings(self):
        """Test that get_nexus_settings returns NexusSettings."""
        settings = dependencies.get_nexus_settings()
        assert isinstance(settings, NexusSettings)

    def test_settings_are_cached(self):
        """Settings providers should use lru_cache and return the same instance."""
        dependencies.get_app_settings.cache_clear()
        settings1 = dependencies.get_app_settings()
        settings2 = dependencies.get_app_settings()
        assert settings1 is settings2


def test_get_github_settings(monkeypatch: MonkeyPatch):
    """Test that get_github_settings returns GitHubSettings."""
    settings = dependencies.get_github_settings()
    assert isinstance(settings, GitHubSettings)
    dependencies.get_github_settings.cache_clear()


class TestLLMClientFactory:
    """Test LLM client factory and provider functions."""

    def test_get_llm_client_mock(self, monkeypatch):
        """Test that get_llm_client returns MockNexusClient when mock is enabled."""
        monkeypatch.setenv("OBS_GLX_USE_MOCK_NEXUS", "true")

        # Clear cache to pick up new env vars
        dependencies.get_nexus_settings.cache_clear()

        client = dependencies.get_llm_client(
            nexus_settings=dependencies.get_nexus_settings(),
        )
        assert isinstance(client, MockNexusClient)

    def test_get_llm_client_real(self, monkeypatch):
        """Test that get_llm_client returns NexusClient when mock is disabled."""
        monkeypatch.setenv("OBS_GLX_USE_MOCK_NEXUS", "false")

        # Clear cache to pick up new env vars
        dependencies.get_nexus_settings.cache_clear()

        client = dependencies.get_llm_client(
            nexus_settings=dependencies.get_nexus_settings(),
        )
        assert isinstance(client, NexusClient)

    def test_get_llm_client_provider(self):
        """Test that get_llm_client_provider returns a callable."""
        provider = dependencies.get_llm_client_provider(
            nexus_settings=dependencies.get_nexus_settings(),
        )
        assert callable(provider)

    def test_llm_client_provider_returns_client(self, monkeypatch):
        """Test that the provider function returns an LLM client."""
        monkeypatch.setenv("OBS_GLX_USE_MOCK_NEXUS", "true")

        # Clear cache
        dependencies.get_nexus_settings.cache_clear()

        provider = dependencies.get_llm_client_provider(
            nexus_settings=dependencies.get_nexus_settings(),
        )
        client = provider()
        assert isinstance(client, MockNexusClient)

    def test_llm_client_provider_ignores_backend_parameter(self, monkeypatch):
        """Test that provider ignores backend parameter (for API compatibility)."""
        monkeypatch.setenv("OBS_GLX_USE_MOCK_NEXUS", "true")

        # Clear cache
        dependencies.get_nexus_settings.cache_clear()

        provider = dependencies.get_llm_client_provider(
            nexus_settings=dependencies.get_nexus_settings(),
        )

        # Request different backends - should all return same client type
        client1 = provider("ollama")
        client2 = provider("mlx")
        client3 = provider(None)

        assert isinstance(client1, MockNexusClient)
        assert isinstance(client2, MockNexusClient)
        assert isinstance(client3, MockNexusClient)


class TestServiceProviders:
    """Test service provider functions."""

    def test_get_vault_service(self):
        """Test that get_vault_service returns VaultServiceProtocol."""
        settings = ObsGlxSettings(vault_submodule_path="/tmp/test_vault")

        vault_service = dependencies.get_vault_service(settings=settings)
        assert vault_service is not None

    def test_get_github_draft_service(self, monkeypatch):
        """Test that get_github_draft_service returns appropriate client."""
        monkeypatch.setenv("OBS_GLX_USE_MOCK_GITHUB", "true")

        # Clear cache
        dependencies.get_app_settings.cache_clear()
        dependencies.get_github_settings.cache_clear()

        client = dependencies.get_github_draft_service(
            settings=dependencies.get_app_settings(),
            github_settings=dependencies.get_github_settings(),
        )
        assert client is not None
        assert isinstance(client, MockGitHubDraftService)

    def test_get_research_client(self, monkeypatch):
        """Test that get_research_client returns appropriate client."""
        monkeypatch.setenv("OBS_GLX_USE_MOCK_STARPROBE", "true")

        # Clear cache
        dependencies.get_app_settings.cache_clear()
        dependencies.get_starprobe_settings.cache_clear()

        client = dependencies.get_research_client(
            settings=dependencies.get_app_settings(),
            starprobe_settings=dependencies.get_starprobe_settings(),
        )
        assert client is not None

    def test_get_redis_client(self, monkeypatch):
        """Test that get_redis_client returns appropriate client."""
        monkeypatch.setenv("OBS_GLX_USE_MOCK_REDIS", "true")

        # Clear cache
        dependencies.get_app_settings.cache_clear()
        dependencies.get_redis_settings.cache_clear()

        client = dependencies.get_redis_client(
            settings=dependencies.get_app_settings(),
            redis_settings=dependencies.get_redis_settings(),
        )
        assert client is not None
