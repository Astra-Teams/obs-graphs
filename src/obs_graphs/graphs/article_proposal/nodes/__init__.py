"""Node modules for Obsidian Vault workflow automation."""

from src.obs_graphs.graphs.article_proposal.state import FileChange, NodeResult

from .node1_article_proposal import ArticleProposalNode
from .node2_deep_research import DeepResearchNode
from .node3_submit_draft_branch import SubmitDraftBranchNode

__all__ = [
    "ArticleProposalNode",
    "DeepResearchNode",
    "SubmitDraftBranchNode",
    "NodeResult",
    "FileChange",
]

