"""Factory for creating workflow graph builders."""

from typing import Callable

from starprobe_sdk import ResearchClientProtocol

from src.obs_glx.graphs.article_proposal.graph import ArticleProposalGraph
from src.obs_glx.graphs.protocol import WorkflowGraphProtocol
from src.obs_glx.protocols import StlConnClientProtocol, VaultServiceProtocol
from src.obs_glx.services.github_draft_service import GitHubDraftServiceProtocol


def get_graph_builder(
    workflow_type: str,
    vault_service: VaultServiceProtocol | None = None,
    llm_client_provider: Callable[[], StlConnClientProtocol] | None = None,
    draft_service: GitHubDraftServiceProtocol | None = None,
    research_client: ResearchClientProtocol | None = None,
) -> WorkflowGraphProtocol:
    """
    Factory function to get appropriate workflow graph builder with dependencies.

    Args:
        workflow_type: Type of workflow to build (e.g., 'article-proposal')
        vault_service: Optional service for vault file operations (uses default if None)
        llm_client_provider: Optional provider function for creating LLM clients (uses default if None)
        draft_service: Optional client for GitHub draft operations (uses default if None)
        research_client: Optional client for deep research operations (uses default if None)

    Returns:
        WorkflowGraphProtocol implementation for the specified type

    Raises:
        ValueError: If workflow_type is unknown

    Supported workflow types:
        - article-proposal: Research topic proposal and article creation
    """
    from src.obs_glx import dependencies

    # Use provided dependencies or get defaults
    vault_service = vault_service or dependencies.get_vault_service()
    llm_client_provider = llm_client_provider or dependencies.get_llm_client_provider(
        stl_conn_settings=dependencies.get_stl_conn_settings(),
    )
    draft_service = draft_service or dependencies.get_github_draft_service(
        settings=dependencies.get_app_settings(),
        github_settings=dependencies.get_github_settings(),
    )
    research_client = research_client or dependencies.get_research_client(
        settings=dependencies.get_app_settings(),
        starprobe_settings=dependencies.get_starprobe_settings(),
    )

    graph_builders = {
        "article-proposal": lambda: ArticleProposalGraph(
            vault_service=vault_service,
            article_proposal_node=dependencies.get_article_proposal_node(
                llm_client_provider=llm_client_provider
            ),
            deep_research_node=dependencies.get_deep_research_node(
                research_client=research_client
            ),
            submit_draft_branch_node=dependencies.get_submit_draft_branch_node(
                draft_service=draft_service
            ),
        ),
        # Future additions can be added here, e.g.:
        # "content-improvement": lambda: dependencies.get_content_improvement_graph(...),
    }

    builder_factory = graph_builders.get(workflow_type)
    if not builder_factory:
        available_types = ", ".join(graph_builders.keys())
        raise ValueError(
            f"Unknown workflow type: '{workflow_type}'. Available types: {available_types}"
        )

    return builder_factory()
