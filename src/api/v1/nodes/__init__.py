"""Node modules for the simplified new article workflow."""

from src.state import AgentResult, FileChange

from .create_pull_request import CreatePullRequestNode
from .deep_search_placeholder import DeepSearchPlaceholderNode
from .extract_keywords import ExtractKeywordsNode
from .generate_themes import GenerateThemesNode
from .select_category import SelectCategoryNode

__all__ = [
    "AgentResult",
    "FileChange",
    "CreatePullRequestNode",
    "DeepSearchPlaceholderNode",
    "ExtractKeywordsNode",
    "GenerateThemesNode",
    "SelectCategoryNode",
]
