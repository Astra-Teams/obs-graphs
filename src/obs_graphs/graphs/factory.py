"""Factory for creating workflow graph builders."""

from typing import Callable

from obs_gtwy_sdk import GatewayClientProtocol
from olm_d_rch_sdk import ResearchClientProtocol

from src.obs_graphs.graphs.article_proposal.graph import ArticleProposalGraph
from src.obs_graphs.graphs.protocol import WorkflowGraphProtocol
from src.obs_graphs.protocols import LLMClientProtocol, VaultServiceProtocol


def get_graph_builder(
    workflow_type: str,
    vault_service: VaultServiceProtocol,
    llm_client_provider: Callable[[str | None], LLMClientProtocol],
    gateway_client: GatewayClientProtocol,
    research_client: ResearchClientProtocol,
) -> WorkflowGraphProtocol:
    """
    Factory function to get appropriate workflow graph builder with dependencies.

    Args:
        workflow_type: Type of workflow to build (e.g., 'article-proposal')
        vault_service: Service for vault file operations
        llm_client_provider: Provider function for creating LLM clients
        gateway_client: Client for Obsidian gateway operations
        research_client: Client for deep research operations

    Returns:
        WorkflowGraphProtocol implementation for the specified type

    Raises:
        ValueError: If workflow_type is unknown

    Supported workflow types:
        - article-proposal: Research topic proposal and article creation
    """
    if workflow_type == "article-proposal":
        return ArticleProposalGraph(
            vault_service=vault_service,
            llm_client_provider=llm_client_provider,
            gateway_client=gateway_client,
            research_client=research_client,
        )

    # Future additions:
    # elif workflow_type == "content-improvement":
    #     return ContentImprovementGraph(...)
    # elif workflow_type == "link-repair":
    #     return LinkRepairGraph(...)

    available_types = ["article-proposal"]
    raise ValueError(
        f"Unknown workflow type: '{workflow_type}'. Available types: {', '.join(available_types)}"
    )
