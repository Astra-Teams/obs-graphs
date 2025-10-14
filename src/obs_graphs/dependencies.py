"""Central dependency injection hub for obs-graphs using FastAPI's Depends mechanism."""

import platform
from functools import lru_cache
from pathlib import Path
from typing import Callable, Generator, Union

import redis
from fastapi import Depends
from obs_gtwy_sdk import GatewayClientProtocol, MockObsGatewayClient, ObsGatewayClient
from olm_d_rch_sdk import ResearchApiClient, ResearchClientProtocol
from sqlalchemy.orm import Session

from dev.mocks_clients import MockRedisClient, MockResearchApiClient
from src.obs_graphs.clients import MLXClient, OllamaClient
from src.obs_graphs.config import (
    DBSettings,
    GatewaySettings,
    MLXSettings,
    ObsGraphsSettings,
    OllamaSettings,
    RedisSettings,
    ResearchAPISettings,
    WorkflowSettings,
)
from src.obs_graphs.db.database import create_db_session
from src.obs_graphs.protocols import LLMClientProtocol, VaultServiceProtocol
from src.obs_graphs.services import VaultService

# ============================================================================
# Configuration Providers
# ============================================================================


@lru_cache()
def get_app_settings() -> ObsGraphsSettings:
    """Get the application settings singleton."""
    return ObsGraphsSettings()


@lru_cache()
def get_ollama_settings() -> OllamaSettings:
    """Get the Ollama settings singleton."""
    return OllamaSettings()


@lru_cache()
def get_mlx_settings() -> MLXSettings:
    """Get the MLX settings singleton."""
    return MLXSettings()


@lru_cache()
def get_gateway_settings() -> GatewaySettings:
    """Get the gateway settings singleton."""
    return GatewaySettings()


@lru_cache()
def get_db_settings() -> DBSettings:
    """Get the database settings singleton."""
    return DBSettings()


@lru_cache()
def get_redis_settings() -> RedisSettings:
    """Get the Redis settings singleton."""
    return RedisSettings()


@lru_cache()
def get_research_api_settings() -> ResearchAPISettings:
    """Get the research API settings singleton."""
    return ResearchAPISettings()


@lru_cache()
def get_workflow_settings() -> WorkflowSettings:
    """Get the workflow settings singleton."""
    return WorkflowSettings()


# ============================================================================
# LLM Client Factory Pattern
# ============================================================================

# Factory dictionary mapping backend names to client constructors
CLIENT_FACTORIES = {
    "ollama": lambda settings: OllamaClient(
        model=settings.model,
        base_url=settings.base_url,
    ),
    "mlx": lambda settings: MLXClient(settings),
}


def get_llm_client(
    settings: ObsGraphsSettings = Depends(get_app_settings),
    ollama_settings: OllamaSettings = Depends(get_ollama_settings),
    mlx_settings: MLXSettings = Depends(get_mlx_settings),
) -> LLMClientProtocol:
    """
    Get an LLM client based on application settings.

    Args:
        settings: Application settings determining which backend to use
        ollama_settings: Ollama-specific configuration
        mlx_settings: MLX-specific configuration

    Returns:
        An LLM client implementing LLMClientProtocol

    Raises:
        ValueError: If the backend is unsupported
        RuntimeError: If MLX is requested on non-ARM64 architecture
    """
    backend = settings.llm_backend.lower()

    # Handle mock mode
    if settings.use_mock_llm:
        from dev.mocks_clients import MockOllamaClient

        return OllamaClient(
            model=ollama_settings.model,
            base_url=ollama_settings.base_url,
            llm=MockOllamaClient(),
        )

    # Validate backend
    if backend not in CLIENT_FACTORIES:
        raise ValueError(f"Unknown LLM backend: {backend}")

    # MLX requires Apple Silicon
    if backend == "mlx":
        machine = platform.machine().lower()
        if machine not in {"arm64", "aarch64"}:
            raise RuntimeError(
                "MLX backend is only supported on Apple Silicon (ARM64/AArch64)."
            )
        return CLIENT_FACTORIES["mlx"](mlx_settings)

    # Default to Ollama
    if backend == "ollama":
        return CLIENT_FACTORIES["ollama"](ollama_settings)

    # Fallback to Ollama (should not reach here due to validation above)
    return CLIENT_FACTORIES["ollama"](ollama_settings)


def get_llm_client_provider(
    settings: ObsGraphsSettings = Depends(get_app_settings),
    ollama_settings: OllamaSettings = Depends(get_ollama_settings),
    mlx_settings: MLXSettings = Depends(get_mlx_settings),
) -> Callable[[str | None], LLMClientProtocol]:
    """
    Get a provider function for LLM clients.

    This is used by nodes that need to create LLM clients with specific backends.

    Returns:
        A callable that accepts an optional backend parameter and returns an LLM client
    """

    def provider(backend: str | None = None) -> LLMClientProtocol:
        target_backend = (backend or settings.llm_backend).strip().lower()

        # Handle mock mode
        if settings.use_mock_llm:
            from dev.mocks_clients import MockOllamaClient

            return OllamaClient(
                model=ollama_settings.model,
                base_url=ollama_settings.base_url,
                llm=MockOllamaClient(),
            )

        # Validate backend
        if target_backend not in CLIENT_FACTORIES:
            raise ValueError(f"Unknown LLM backend: {target_backend}")

        # MLX requires Apple Silicon
        if target_backend == "mlx":
            machine = platform.machine().lower()
            if machine not in {"arm64", "aarch64"}:
                raise RuntimeError(
                    "MLX backend is only supported on Apple Silicon (ARM64/AArch64)."
                )
            return CLIENT_FACTORIES["mlx"](mlx_settings)

        # Ollama
        if target_backend == "ollama":
            return CLIENT_FACTORIES["ollama"](ollama_settings)

        # Fallback
        return CLIENT_FACTORIES["ollama"](ollama_settings)

    return provider


# ============================================================================
# Database Session Provider
# ============================================================================


def get_db_session() -> Generator[Session, None, None]:
    """
    Provide a database session.

    Yields:
        SQLAlchemy Session instance
    """
    db = create_db_session()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Service Providers
# ============================================================================


def get_vault_service(
    settings: ObsGraphsSettings = Depends(get_app_settings),
) -> VaultServiceProtocol:
    """
    Get the vault service instance.

    Args:
        settings: Application settings containing vault path

    Returns:
        VaultService configured with the vault path from settings
    """
    return VaultService(vault_path=Path(settings.vault_submodule_path))


def get_gateway_client(
    settings: ObsGraphsSettings = Depends(get_app_settings),
    gateway_settings: GatewaySettings = Depends(get_gateway_settings),
) -> GatewayClientProtocol:
    """
    Get the obs-gtwy gateway client instance.

    Args:
        settings: Application settings for mock configuration
        gateway_settings: Gateway-specific configuration

    Returns:
        Gateway client (mock or real based on settings)
    """
    if settings.use_mock_obs_gateway:
        return MockObsGatewayClient()

    gateway_base = str(gateway_settings.base_url).rstrip("/")
    return ObsGatewayClient(base_url=gateway_base)


def get_research_client(
    settings: ObsGraphsSettings = Depends(get_app_settings),
    research_settings: ResearchAPISettings = Depends(get_research_api_settings),
) -> ResearchClientProtocol:
    """
    Get the research API client instance.

    Args:
        settings: Application settings for mock configuration
        research_settings: Research API-specific configuration

    Returns:
        Research client (mock or real based on settings)
    """
    if settings.use_mock_ollama_deep_researcher:
        return MockResearchApiClient()

    return ResearchApiClient(
        base_url=str(research_settings.research_api_url).rstrip("/"),
        timeout=research_settings.research_api_timeout_seconds,
    )


def get_redis_client(
    settings: ObsGraphsSettings = Depends(get_app_settings),
    redis_settings: RedisSettings = Depends(get_redis_settings),
) -> Union[redis.Redis, "redis.FakeRedis"]:
    """
    Get the Redis client instance.

    Args:
        settings: Application settings for mock configuration
        redis_settings: Redis-specific configuration

    Returns:
        Redis client (FakeRedis if mocking, otherwise real Redis)
    """
    if settings.use_mock_redis:
        return MockRedisClient.get_client()

    return redis.Redis.from_url(redis_settings.celery_broker_url, decode_responses=True)


# ============================================================================
# Node Providers
# ============================================================================


def get_article_proposal_node(
    llm_client_provider: Callable[[str | None], LLMClientProtocol] = Depends(
        get_llm_client_provider
    ),
):
    """
    Get the article proposal node.

    Args:
        llm_client_provider: Provider function for creating LLM clients

    Returns:
        ArticleProposalNode configured with LLM client provider
    """
    from src.obs_graphs.graphs.article_proposal.nodes.node1_article_proposal import (
        ArticleProposalNode,
    )

    return ArticleProposalNode(llm_client_provider)


def get_deep_research_node(
    research_client: ResearchClientProtocol = Depends(get_research_client),
):
    """
    Get the deep research node.

    Args:
        research_client: Research client for deep research operations

    Returns:
        DeepResearchNode configured with research client
    """
    from src.obs_graphs.graphs.article_proposal.nodes.node2_deep_research import (
        DeepResearchNode,
    )

    return DeepResearchNode(research_client)


def get_submit_pull_request_node(
    gateway_client: GatewayClientProtocol = Depends(get_gateway_client),
):
    """
    Get the submit pull request node.

    Args:
        gateway_client: Gateway client for Obsidian operations

    Returns:
        SubmitPullRequestNode configured with gateway client
    """
    from src.obs_graphs.graphs.article_proposal.nodes.node3_submit_pull_request import (
        SubmitPullRequestNode,
    )

    return SubmitPullRequestNode(gateway_client)
