"""Factory for creating workflow graph builders."""

from src.obs_graphs.graphs.article_proposal.graph import ArticleProposalGraph
from src.obs_graphs.graphs.protocol import WorkflowGraphProtocol


def get_graph_builder(workflow_type: str) -> WorkflowGraphProtocol:
    """
    Factory function to get appropriate workflow graph builder.

    Args:
        workflow_type: Type of workflow to build (e.g., 'article-proposal')

    Returns:
        WorkflowGraphProtocol implementation for the specified type

    Raises:
        ValueError: If workflow_type is unknown

    Supported workflow types:
        - article-proposal: Research topic proposal and article creation
    """
    graphs = {
        "article-proposal": ArticleProposalGraph,
        # Future additions:
        # "content-improvement": ContentImprovementGraph,
        # "link-repair": LinkRepairGraph,
    }

    graph_class = graphs.get(workflow_type)
    if not graph_class:
        available = ", ".join(graphs.keys())
        raise ValueError(
            f"Unknown workflow type: '{workflow_type}'. Available types: {available}"
        )

    return graph_class()
