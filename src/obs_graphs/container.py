"""Dependency injection container for the Obsidian Vault workflow application."""

import platform
from pathlib import Path
from typing import Dict, Optional, Union

import redis

from src.obs_graphs.clients import MLXClient, ObsGatewayClient, OllamaClient
from src.obs_graphs.config import (
    gateway_settings,
    mlx_settings,
    obs_graphs_settings,
    ollama_settings,
    redis_settings,
    research_api_settings,
)
from src.obs_graphs.protocols import (
    GatewayClientProtocol,
    LLMClientProtocol,
    NodeProtocol,
    ResearchClientProtocol,
    VaultServiceProtocol,
)
from src.obs_graphs.services import VaultService


class DependencyContainer:
    """Container for managing application dependencies with lazy instantiation."""

    def __init__(self):
        """Initialize the container with empty caches."""
        self._vault_service: Optional[VaultServiceProtocol] = None
        self._research_client: Optional[ResearchClientProtocol] = None
        self._nodes: Dict[str, NodeProtocol] = {}
        self._ollama_client: Optional[LLMClientProtocol] = None
        self._mlx_client: Optional[LLMClientProtocol] = None
        self._mock_llm_client: Optional[LLMClientProtocol] = None
        self._redis_client: Optional[Union[redis.Redis, "redis.FakeRedis"]] = None
        self._current_branch: Optional[str] = None
        self._vault_path: Optional[Path] = None
        self._gateway_client: Optional[GatewayClientProtocol] = None

    def set_branch(self, branch: str) -> None:
        """
        Set the current branch for the workflow.

        The value is retained for backward compatibility with legacy workflows.
        """
        self._current_branch = branch
        # Branch state no longer influences vault service caching but we keep the
        # assignment for backward compatibility with existing callers.

    def set_vault_path(self, vault_path: Path) -> None:
        """Set the local vault path used during workflow execution."""
        self._vault_path = vault_path
        if self._vault_service is not None and hasattr(
            self._vault_service, "set_vault_path"
        ):
            self._vault_service.set_vault_path(vault_path)

    def get_vault_service(self, branch: Optional[str] = None) -> VaultServiceProtocol:
        """
        Get the vault service instance for reading the local vault copy.

        Args:
            branch: Deprecated. Present for backward compatibility.

        Returns:
            VaultService configured with the currently registered vault path.
        """
        if branch:
            # Direct branch specification kept for backward compatibility
            return VaultService(self._vault_path)

        if self._vault_service is None:
            self._vault_service = VaultService(self._vault_path)
        return self._vault_service

    def get_gateway_client(self) -> GatewayClientProtocol:
        """Return the obs-gtwy gateway client implementation."""
        if self._gateway_client is None:
            gateway_base = str(gateway_settings.base_url).rstrip("/")
            gateway_timeout = gateway_settings.timeout_seconds

            if obs_graphs_settings.use_mock_obs_gateway:
                from mock_obs_gtwy_client.mock_obs_gtwy_client import (
                    MockObsGtwyClient,
                )

                class AdaptedMockGateway(GatewayClientProtocol):
                    def __init__(self):
                        self._client = MockObsGtwyClient()

                    def create_draft_branch(
                        self, *, file_name: str, content: str, branch_name: str
                    ) -> str:
                        if branch_name:
                            return branch_name
                        response = self._client.create_draft(file_name, content)
                        derived = response.get("branch_name")
                        if not isinstance(derived, str) or not derived.strip():
                            slug = (
                                Path(file_name).stem.replace(" ", "-").lower()
                                or "draft"
                            )
                            return f"draft/{slug}"
                        return derived.strip()

                self._gateway_client = AdaptedMockGateway()
            else:
                self._gateway_client = ObsGatewayClient(
                    base_url=gateway_base,
                    timeout_seconds=gateway_timeout,
                )
        return self._gateway_client

    def get_research_client(self) -> ResearchClientProtocol:
        """
        Get the research API client instance.

        Returns either the mock adapter or the real HTTP client depending on
        the USE_MOCK_OLLAMA_DEEP_RESEARCHER setting.
        """
        if self._research_client is None:
            if obs_graphs_settings.use_mock_ollama_deep_researcher:
                from mock_olm_d_rch_client.mock_olm_d_rch_client import (
                    MockOlmDRchClient,
                )

                from src.obs_graphs.protocols.research_client_protocol import (
                    ResearchResult,
                )

                class AdaptedMockClient:
                    def __init__(self):
                        self.client = MockOlmDRchClient()

                    def run_research(
                        self, query: str, backend: Optional[str] = None
                    ) -> ResearchResult:
                        result = self.client.research(query)
                        article = result["article"]
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

                api_settings = research_api_settings
                self._research_client = ResearchApiClient(
                    base_url=api_settings.research_api_url,
                    timeout=api_settings.research_api_timeout_seconds,
                )
        return self._research_client

    def provide_llm_client(self, backend: Optional[str] = None) -> LLMClientProtocol:
        """
        Get an LLM client for the requested backend.

        Args:
            backend: Optional backend identifier ("ollama" or "mlx").

        Returns:
            An LLM client implementing LLMClientProtocol.
        """
        target_backend = (backend or obs_graphs_settings.llm_backend).strip().lower()
        if target_backend not in {"ollama", "mlx"}:
            raise ValueError(f"Unsupported LLM backend: {target_backend}")

        if obs_graphs_settings.use_mock_llm:
            return self._get_mock_llm_client()

        if target_backend == "mlx":
            return self._get_mlx_client()

        return self._get_ollama_client()

    def get_llm(self) -> LLMClientProtocol:
        """Return the default LLM client configured for the application."""
        return self.provide_llm_client()

    def _get_mock_llm_client(self) -> LLMClientProtocol:
        if self._mock_llm_client is None:
            from dev.mocks_clients import MockOllamaClient

            self._mock_llm_client = OllamaClient(
                model=ollama_settings.model,
                base_url=ollama_settings.base_url,
                llm=MockOllamaClient(),
            )
        return self._mock_llm_client

    def _get_ollama_client(self) -> LLMClientProtocol:
        if self._ollama_client is None:
            self._ollama_client = OllamaClient(
                model=ollama_settings.model,
                base_url=ollama_settings.base_url,
            )
        return self._ollama_client

    def _get_mlx_client(self) -> LLMClientProtocol:
        machine = platform.machine().lower()
        if machine not in {"arm64", "aarch64"}:
            raise RuntimeError(
                "MLX backend is only supported on Apple Silicon (ARM64/AArch64)."
            )

        if self._mlx_client is None:
            self._mlx_client = MLXClient(
                model=mlx_settings.model,
                max_tokens=mlx_settings.max_tokens,
                temperature=mlx_settings.temperature,
                top_p=mlx_settings.top_p,
            )
        return self._mlx_client

    def get_redis_client(self) -> Union[redis.Redis, "redis.FakeRedis"]:
        """
        Get the Redis client instance.

        Returns FakeRedis if USE_MOCK_REDIS=True, otherwise redis.Redis.
        """
        if self._redis_client is None:
            if obs_graphs_settings.use_mock_redis:
                from dev.mocks_clients import MockRedisClient

                self._redis_client = MockRedisClient.get_client()
            else:
                self._redis_client = redis.Redis.from_url(
                    redis_settings.celery_broker_url, decode_responses=True
                )
        return self._redis_client

    def get_node(self, name: str) -> NodeProtocol:
        """Get a node instance by name."""
        if name not in self._nodes:
            # Import all node classes and find the one with matching name
            from src.obs_graphs.graphs.article_proposal.nodes.node1_article_proposal import (
                ArticleProposalAgent,
            )
            from src.obs_graphs.graphs.article_proposal.nodes.node2_deep_research import (
                DeepResearchAgent,
            )
            from src.obs_graphs.graphs.article_proposal.nodes.node3_submit_pull_request import (
                SubmitPullRequestAgent,
            )

            node_classes = [
                ArticleProposalAgent,
                DeepResearchAgent,
                SubmitPullRequestAgent,
            ]

            node_class = None
            for cls in node_classes:
                if hasattr(cls, "name") and cls.name == name:
                    node_class = cls
                    break

            if node_class is None:
                raise ValueError(f"Unknown node: {name}")

            # Instantiate with dependencies
            if name == "article_proposal":
                self._nodes[name] = node_class(self.provide_llm_client)
            elif name == "submit_pull_request":
                self._nodes[name] = node_class(self.get_gateway_client())
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
