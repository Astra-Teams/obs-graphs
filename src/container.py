"""Dependency injection container for the Obsidian Vault workflow application."""

from typing import Dict, Optional

from src.clients.github_client import GithubClient
from src.nodes.article_improvement import ArticleImprovementAgent
from src.nodes.category_organization import CategoryOrganizationAgent
from src.nodes.cross_reference import CrossReferenceAgent
from src.nodes.file_organization import FileOrganizationAgent
from src.nodes.new_article_creation import NewArticleCreationAgent
from src.nodes.quality_audit import QualityAuditAgent
from src.protocols import GithubClientProtocol, NodeProtocol, VaultServiceProtocol
from src.services.vault import VaultService


class DependencyContainer:
    """Container for managing application dependencies with lazy instantiation."""

    def __init__(self):
        """Initialize the container with empty caches."""
        self._github_client: Optional[GithubClientProtocol] = None
        self._vault_service: Optional[VaultServiceProtocol] = None
        self._nodes: Dict[str, NodeProtocol] = {}
        self._graph_builder = None  # Will be implemented in Phase 3

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
        """Get the GitHub client instance."""
        if self._github_client is None:
            self._github_client = GithubClient()
        return self._github_client

    def get_vault_service(self) -> VaultServiceProtocol:
        """Get the vault service instance."""
        if self._vault_service is None:
            self._vault_service = VaultService()
        return self._vault_service

    def get_node(self, name: str) -> NodeProtocol:
        """Get a node instance by name."""
        if name not in self._nodes:
            if name not in self._node_classes:
                raise ValueError(f"Unknown node: {name}")
            self._nodes[name] = self._node_classes[name]()
        return self._nodes[name]

    def get_graph_builder(self):
        """Get the graph builder instance."""
        # TODO: Implement in Phase 3 when GraphBuilder is created
        raise NotImplementedError("GraphBuilder not yet implemented")


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container instance."""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container
