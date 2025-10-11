"""Node modules for Obsidian Vault workflow automation."""

from src.obs_graphs.graphs.article_proposal.state import AgentResult, FileChange

from .node1_article_proposal import ArticleProposalAgent
from .node2_deep_research import DeepResearchAgent
from .node3_submit_pull_request import SubmitPullRequestAgent

__all__ = [
    "ArticleProposalAgent",
    "DeepResearchAgent",
    "SubmitPullRequestAgent",
    "AgentResult",
    "FileChange",
]
