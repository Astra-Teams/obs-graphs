"""Dependency injection container for the Obsidian Vault workflow application."""

from pathlib import Path
from typing import Dict, Optional, Union

import redis
from langchain_core.language_models.llms import BaseLLM
from langchain_ollama import OllamaLLM

from src.obs_graphs.clients import GithubClient
from src.obs_graphs.protocols import (
    GithubClientProtocol,
    NodeProtocol,
    ResearchClientProtocol,
    VaultServiceProtocol,
)
from src.obs_graphs.services import VaultService
from src.obs_graphs.settings import settings


class DependencyContainer:
    """Container for managing application dependencies with lazy instantiation."""

    def __init__(self):
        """Initialize the container with empty caches."""
        self._github_client: Optional[GithubClientProtocol] = None
        self._vault_service: Optional[VaultServiceProtocol] = None
        self._research_client: Optional[ResearchClientProtocol] = None
        self._nodes: Dict[str, NodeProtocol] = {}
        self._llm: Optional[BaseLLM] = None
        self._redis_client: Optional[Union[redis.Redis, "redis.FakeRedis"]] = None
        self._current_branch: Optional[str] = None
        self._vault_path: Optional[Path] = None

    def get_github_client(self) -> GithubClientProtocol:
        """
        Get the GitHub client instance.

        Returns MockGithubClient if USE_MOCK_GITHUB=True, otherwise GithubClient.
        """
        if self._github_client is None:
            if settings.use_mock_github:
                from dev.mocks_clients import MockGithubClient

                self._github_client = MockGithubClient()
            else:
                self._github_client = GithubClient(settings)
        return self._github_client

    def set_branch(self, branch: str) -> None:
        """
        Set the current branch for the workflow.

        This must be called before get_vault_service().
        """
        self._current_branch = branch
        # Clear cached vault service when branch changes
        self._vault_service = None
        # Clear cached nodes that depend on vault service
        if "commit_changes" in self._nodes:
            del self._nodes["commit_changes"]

    def set_vault_path(self, vault_path: Path) -> None:
        """Set the local vault path used during workflow execution."""
        self._vault_path = vault_path
        if self._vault_service is not None and hasattr(
            self._vault_service, "set_vault_path"
        ):
            self._vault_service.set_vault_path(vault_path)

    def get_vault_service(self, branch: Optional[str] = None) -> VaultServiceProtocol:
        """
        Get the vault service instance for a specific branch.

        Args:
            branch: Branch name. If not provided, uses current branch set by set_branch().

        Returns:
            VaultService configured for the specified branch.

        Raises:
            ValueError: If no branch is specified and no current branch is set.
        """
        if branch:
            # Direct branch specification (used by ArticleProposalGraph)
            service = VaultService(self.get_github_client(), branch, self._vault_path)
            return service

        if self._current_branch is None:
            raise ValueError(
                "No branch specified. Call set_branch() or provide branch parameter."
            )

        if self._vault_service is None:
            self._vault_service = VaultService(
                self.get_github_client(), self._current_branch, self._vault_path
            )
        return self._vault_service

    def get_research_client(self) -> ResearchClientProtocol:
        """
        Get the research API client instance.

        Returns either the mock adapter or the real HTTP client depending on
        the USE_MOCK_OLLAMA_DEEP_RESEARCHER setting.
        """
        if self._research_client is None:
            if settings.use_mock_ollama_deep_researcher:
                import sys
                from importlib.util import module_from_spec, spec_from_file_location
                from pathlib import Path

                from src.obs_graphs.protocols.research_client_protocol import (
                    ResearchResult,
                )

                submodules_path = Path(__file__).parent.parent / "submodules"
                if str(submodules_path) not in sys.path:
                    sys.path.insert(0, str(submodules_path))

                mock_client_path = (
                    submodules_path
                    / "ollama-deep-researcher"
                    / "sdk"
                    / "mock_ollama_deep_researcher_client"
                    / "mock_ollama_deep_researcher_client.py"
                )
                spec = spec_from_file_location("mock_client", mock_client_path)
                mock_module = module_from_spec(spec)
                spec.loader.exec_module(mock_module)
                MockOllamaDeepResearcherClient = (
                    mock_module.MockOllamaDeepResearcherClient
                )

                class AdaptedMockClient:
                    def __init__(self):
                        self.client = MockOllamaDeepResearcherClient()

                    def run_research(self, query: str) -> ResearchResult:
                        result = self.client.research(query)
                        article = result.get("article")
                        if not isinstance(article, str) or not article.strip():
                            raise ValueError(
                                "Mock research client returned empty article"
                            )

                        metadata = result.get("metadata") or {}
                        if not isinstance(metadata, dict):
                            metadata = {}

                        diagnostics = result.get("diagnostics") or []
                        if not isinstance(diagnostics, list):
                            diagnostics = [str(diagnostics)]

                        return ResearchResult(
                            article=article,
                            metadata=metadata,
                            diagnostics=[str(item) for item in diagnostics],
                            processing_time=result.get("processing_time"),
                        )

                self._research_client = AdaptedMockClient()
            else:
                from src.obs_graphs.clients.research_api_client import ResearchApiClient

                api_settings = settings.research_api_settings
                self._research_client = ResearchApiClient(
                    base_url=api_settings.research_api_url,
                    timeout=api_settings.research_api_timeout_seconds,
                )
        return self._research_client

    def get_llm(self) -> BaseLLM:
        """
        Get the LLM instance.

        Returns MockOllamaClient if USE_MOCK_LLM=True, otherwise OllamaLLM.
        """
        if self._llm is None:
            if settings.use_mock_llm:
                from dev.mocks_clients import MockOllamaClient

                self._llm = MockOllamaClient()
            else:
                self._llm = OllamaLLM(
                    model=settings.llm_model, base_url=settings.ollama_host
                )
        return self._llm

    def get_redis_client(self) -> Union[redis.Redis, "redis.FakeRedis"]:
        """
        Get the Redis client instance.

        Returns FakeRedis if USE_MOCK_REDIS=True, otherwise redis.Redis.
        """
        if self._redis_client is None:
            if settings.use_mock_redis:
                from dev.mocks_clients import MockRedisClient

                self._redis_client = MockRedisClient.get_client()
            else:
                self._redis_client = redis.Redis.from_url(
                    settings.redis_settings.celery_broker_url, decode_responses=True
                )
        return self._redis_client

    def get_node(self, name: str) -> NodeProtocol:
        """Get a node instance by name."""
        if name not in self._nodes:
            # Import all node classes and find the one with matching name
            from src.obs_graphs.graphs.article_proposal.nodes.article_proposal import (
                ArticleProposalAgent,
            )
            from src.obs_graphs.graphs.article_proposal.nodes.article_content_generation import (
                ArticleContentGenerationAgent,
            )
            from src.obs_graphs.graphs.article_proposal.nodes.commit_changes import (
                CommitChangesAgent,
            )
            from src.obs_graphs.graphs.article_proposal.nodes.deep_research import (
                DeepResearchAgent,
            )
            from src.obs_graphs.graphs.article_proposal.nodes.github_pr_creation import (
                GithubPRCreationAgent,
            )

            node_classes = [
                ArticleProposalAgent,
                ArticleContentGenerationAgent,
                CommitChangesAgent,
                DeepResearchAgent,
                GithubPRCreationAgent,
            ]

            node_class = None
            for cls in node_classes:
                if hasattr(cls, 'name') and cls.name == name:
                    node_class = cls
                    break

            if node_class is None:
                raise ValueError(f"Unknown node: {name}")

            # Instantiate with dependencies
            if name in ["article_proposal", "article_content_generation"]:
                self._nodes[name] = node_class(self.get_llm())
            elif name == "commit_changes":
                self._nodes[name] = node_class(self.get_vault_service())
            elif name == "github_pr_creation":
                self._nodes[name] = node_class(
                    self.get_github_client(), self.get_vault_service()
                )
            elif name == "deep_research":
                self._nodes[name] = node_class(self.get_research_client())
            else:
                self._nodes[name] = node_class()
        return self._nodes[name]

    def get_graph_builder(self):
        """Get the graph builder instance."""
        from src.obs_graphs.graphs.article_proposal.graph import ArticleProposalGraph

        return ArticleProposalGraph()


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container instance."""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container
