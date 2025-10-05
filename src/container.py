"""Dependency injection container for the Obsidian Vault workflow application."""

from typing import Dict, Optional, Union

import redis

from src.clients import GithubClient, OllamaClient
from src.protocols import GithubClientProtocol, NodeProtocol, VaultServiceProtocol
from src.services import VaultService
from src.settings import get_settings


class DependencyContainer:
    """Container for managing application dependencies with lazy instantiation."""

    def __init__(self):
        """Initialize the container with empty caches."""
        self._github_client: Optional[GithubClientProtocol] = None
        self._vault_service: Optional[VaultServiceProtocol] = None
        self._nodes: Dict[str, NodeProtocol] = {}
        self._ollama_client: Optional[OllamaClient] = None
        self._redis_client: Optional[Union[redis.Redis, "redis.FakeRedis"]] = None

        # Registry of node classes (module, class_name)
        self._node_classes = {
            "select_category": (
                "src.api.v1.nodes.select_category",
                "SelectCategoryNode",
            ),
            "extract_keywords": (
                "src.api.v1.nodes.extract_keywords",
                "ExtractKeywordsNode",
            ),
            "generate_themes": (
                "src.api.v1.nodes.generate_themes",
                "GenerateThemesNode",
            ),
            "deep_search_placeholder": (
                "src.api.v1.nodes.deep_search_placeholder",
                "DeepSearchPlaceholderNode",
            ),
            "create_pull_request": (
                "src.api.v1.nodes.create_pull_request",
                "CreatePullRequestNode",
            ),
        }

    def get_github_client(self) -> GithubClientProtocol:
        """Get the GitHub client instance."""
        if self._github_client is None:
            settings = get_settings()
            if settings.USE_MOCK_GITHUB:
                from dev.mocks_clients import MockGithubClient

                self._github_client = MockGithubClient()
            else:
                self._github_client = GithubClient(settings)
        return self._github_client

    def get_vault_service(self) -> VaultServiceProtocol:
        """Get the vault service instance."""
        if self._vault_service is None:
            self._vault_service = VaultService()
        return self._vault_service

    def get_ollama_client(self) -> OllamaClient:
        """Return an Ollama client instance."""
        if self._ollama_client is None:
            settings = get_settings()
            if settings.USE_MOCK_LLM:
                from dev.mocks_clients import MockOllamaClient

                self._ollama_client = OllamaClient.from_llm(MockOllamaClient())
            else:
                self._ollama_client = OllamaClient(
                    model=settings.OLLAMA_MODEL,
                    base_url=settings.OLLAMA_BASE_URL,
                )
        return self._ollama_client

    def get_redis_client(self) -> Union[redis.Redis, "redis.FakeRedis"]:
        """Get the Redis client instance."""
        if self._redis_client is None:
            settings = get_settings()
            if settings.USE_MOCK_REDIS:
                from dev.mocks_clients import MockRedisClient

                self._redis_client = MockRedisClient.get_client()
            else:
                self._redis_client = redis.Redis.from_url(
                    settings.CELERY_BROKER_URL, decode_responses=True
                )
        return self._redis_client

    def get_node(self, name: str) -> NodeProtocol:
        """Get a node instance by name."""
        if name not in self._nodes:
            if name not in self._node_classes:
                raise ValueError(f"Unknown node: {name}")

            module_name, class_name = self._node_classes[name]
            import importlib

            module = importlib.import_module(module_name)
            node_class = getattr(module, class_name)
            self._nodes[name] = node_class(self)
        return self._nodes[name]

    def get_graph_builder(self):
        """Get the graph builder instance."""
        from src.api.v1.graph import GraphBuilder

        return GraphBuilder(self)


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container instance."""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container
