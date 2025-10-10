"""Node modules for Obsidian Vault workflow automation."""

from src.obs_graphs.graphs.article_proposal.state import AgentResult, FileChange

from .article_content_generation import ArticleContentGenerationAgent
from .article_proposal import ArticleProposalAgent
from .deep_research import DeepResearchAgent
from .submit_pull_request import SubmitPullRequestAgent

__all__ = [
    "ArticleContentGenerationAgent",
    "ArticleProposalAgent",
    "DeepResearchAgent",
    "SubmitPullRequestAgent",
    "AgentResult",
    "FileChange",
]
