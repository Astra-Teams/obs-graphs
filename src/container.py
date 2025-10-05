"""Dependency injection container for the Obsidian Vault workflow application."""

from typing import Dict, Optional

from langchain_community.llms import Ollama
from langchain_core.language_models.llms import BaseLLM

from src.api.v1.nodes.article_improvement import ArticleImprovementAgent
from src.api.v1.nodes.category_organization import CategoryOrganizationAgent
from src.api.v1.nodes.cross_reference import CrossReferenceAgent
from src.api.v1.nodes.file_organization import FileOrganizationAgent
from src.api.v1.nodes.new_article_creation import NewArticleCreationAgent
from src.api.v1.nodes.quality_audit import QualityAuditAgent
from src.clients.github_client import GithubClient
from src.clients.mock_github_client import MockGithubClient
from src.clients.mock_ollama_client import MockOllamaClient
from src.clients.mock_redis_client import MockRedisClient
from src.protocols import GithubClientProtocol, NodeProtocol, VaultServiceProtocol
from src.services.vault import VaultService
from src.settings import get_settings


class DependencyContainer:
    """Container for managing application dependencies with lazy instantiation."""

    def __init__(self):
        """Initialize the container with empty caches."""
        self._github_client: Optional[GithubClientProtocol] = None
        self._vault_service: Optional[VaultServiceProtocol] = None
        self._nodes: Dict[str, NodeProtocol] = {}
        self._llm: Optional[BaseLLM] = None
        self._redis_client = None

        # Registry of node classes
        self._node_classes = {
            "article_improvement": ArticleImprovementAgent,
            "category_organization": CategoryOrganizationAgent,
            "cross_reference": CrossReferenceAgent,
            "file_organization": FileOrganizationAgent,
            "new_article_creation": NewArticleCreationAgent,
            "quality_audit": QualityAuditAgent,
        }

    def get_github_client(self) -> GithubClientProtocol:
        """
        Get the GitHub client instance.

        Returns MockGithubClient if DEBUG=True, otherwise GithubClient.
        """
        if self._github_client is None:
            settings = get_settings()
            if settings.DEBUG:
                self._github_client = MockGithubClient()
            else:
                self._github_client = GithubClient(settings)
        return self._github_client

    def get_vault_service(self) -> VaultServiceProtocol:
        """Get the vault service instance."""
        if self._vault_service is None:
            self._vault_service = VaultService()
        return self._vault_service

    def get_llm(self) -> BaseLLM:
        """
        Get the LLM instance.

        Returns MockOllamaClient if DEBUG=True, otherwise Ollama.
        """
        if self._llm is None:
            settings = get_settings()
            if settings.DEBUG:
                self._llm = MockOllamaClient()
            else:
                self._llm = Ollama(
                    model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL
                )
        return self._llm

    def get_redis_client(self):
        """
        Get the Redis client instance.

        Returns FakeRedis if DEBUG=True, otherwise redis.Redis.
        """
        if self._redis_client is None:
            settings = get_settings()
            if settings.DEBUG:
                self._redis_client = MockRedisClient.get_client()
            else:
                import redis

                self._redis_client = redis.Redis.from_url(
                    settings.CELERY_BROKER_URL, decode_responses=True
                )
        return self._redis_client

    def get_node(self, name: str) -> NodeProtocol:
        """Get a node instance by name."""
        if name not in self._nodes:
            if name not in self._node_classes:
                raise ValueError(f"Unknown node: {name}")

            # Instantiate with dependencies
            if name == "new_article_creation":
                self._nodes[name] = self._node_classes[name](self.get_llm())
            else:
                self._nodes[name] = self._node_classes[name]()
        return self._nodes[name]

    def get_graph_builder(self):
        """Get the graph builder instance."""
        from src.api.v1.graph import GraphBuilder

        return GraphBuilder()


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container instance."""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container
