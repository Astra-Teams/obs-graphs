"""Node modules for Obsidian Vault workflow automation."""

from src.obs_graphs.graphs.article_proposal.state import NodeResult, FileChange

from .node1_article_proposal import ArticleProposalNode
from .node2_deep_research import DeepResearchNode
from .node3_submit_pull_request import SubmitPullRequestNode

__all__ = [
    "ArticleProposalNode",
    "DeepResearchNode",
    "SubmitPullRequestNode",
    "NodeResult",
    "FileChange",
]
