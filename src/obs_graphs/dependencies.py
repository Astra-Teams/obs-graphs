"""Central dependency injection hub for obs-graphs using FastAPI's Depends mechanism."""

from functools import lru_cache
from pathlib import Path
from typing import Callable, Generator, Union

import redis
from fastapi import Depends
from obs_gtwy_sdk import GatewayClientProtocol, MockObsGatewayClient, ObsGatewayClient
from olm_d_rch_sdk import ResearchApiClient, ResearchClientProtocol
from sqlalchemy.orm import Session
from stl_conn_sdk.stl_conn_client import MockStlConnClient, StlConnClient

from dev.mocks.clients import MockRedisClient, MockResearchApiClient
from src.obs_graphs.config import (
    DBSettings,
    GatewaySettings,
    ObsGraphsSettings,
    RedisSettings,
    ResearchAPISettings,
    StlConnSettings,
    WorkflowSettings,
)
from src.obs_graphs.db.database import create_db_session
from src.obs_graphs.protocols import (
    StlConnClientProtocol,
    VaultServiceProtocol,
)
from src.obs_graphs.services import VaultService

# ============================================================================
# Configuration Providers
# ============================================================================


@lru_cache()
def get_app_settings() -> ObsGraphsSettings:
    """Get the application settings singleton."""
    return ObsGraphsSettings()


@lru_cache()
def get_stl_conn_settings() -> StlConnSettings:
    """Get the Stella Connector settings singleton."""
    return StlConnSettings()


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
# LLM Client via Stella Connector (stl-conn)
# ============================================================================


def _create_llm_client(stl_conn_settings: StlConnSettings) -> StlConnClientProtocol:
    """
    Create an LLM client using the Stella Connector SDK.

    Args:
        stl_conn_settings: Stella Connector configuration

    Returns:
        An LLM client implementing StlConnClientProtocol
    """
    if stl_conn_settings.use_mock_stl_conn:
        return MockStlConnClient(response_format="langchain")
    return StlConnClient(
        base_url=stl_conn_settings.stl_conn_base_url,
        response_format="langchain",
        timeout=stl_conn_settings.stl_conn_timeout,
    )


def get_llm_client(
    stl_conn_settings: StlConnSettings = Depends(get_stl_conn_settings),
) -> StlConnClientProtocol:
    """
    Get an LLM client via Stella Connector.

    Args:
        stl_conn_settings: Stella Connector configuration

    Returns:
        An LLM client implementing StlConnClientProtocol
    """
    return _create_llm_client(stl_conn_settings)


def get_llm_client_provider(
    stl_conn_settings: StlConnSettings = Depends(get_stl_conn_settings),
) -> Callable[[str | None], StlConnClientProtocol]:
    """
    Get a provider function for LLM clients.

    The backend parameter is kept for API compatibility but is ignored
    since stl-conn handles backend selection internally.

    Returns:
        A callable that returns an LLM client via Stella Connector
    """

    def provider(backend: str | None = None) -> StlConnClientProtocol:
        # Backend parameter is ignored - stl-conn handles backend selection
        return _create_llm_client(stl_conn_settings)

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
    llm_client_provider: Callable[[str | None], StlConnClientProtocol] = Depends(
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


def get_submit_draft_branch_node(
    gateway_client: GatewayClientProtocol = Depends(get_gateway_client),
):
    """
    Get the submit draft branch node.

    Args:
        gateway_client: Gateway client for Obsidian operations

    Returns:
        SubmitDraftBranchNode configured with gateway client
    """
    from src.obs_graphs.graphs.article_proposal.nodes.node3_submit_draft_branch import (
        SubmitDraftBranchNode,
    )

    return SubmitDraftBranchNode(gateway_client)
