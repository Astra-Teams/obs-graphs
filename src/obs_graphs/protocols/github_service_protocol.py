"""Protocol definition for high-level GitHub service operations."""

from typing import List, Protocol

from src.obs_graphs.graphs.article_proposal.state import FileChange


class GithubServiceProtocol(Protocol):
    """Protocol for orchestrating GitHub write operations."""

    def commit_and_create_pr(
        self,
        branch_name: str,
        base_branch: str,
        changes: List[FileChange],
        commit_message: str,
        pr_title: str,
        pr_body: str,
    ) -> str:
        """Create branch, commit changes, open a pull request, and return its URL."""
        ...
