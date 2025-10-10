"""Service for orchestrating GitHub branch, commit, and pull request operations."""

from typing import List

from src.obs_graphs.graphs.article_proposal.state import FileChange
from src.obs_graphs.protocols import GithubClientProtocol, GithubServiceProtocol


class GithubService(GithubServiceProtocol):
    """High-level service that chains GitHub write operations in a single call."""

    def __init__(self, github_client: GithubClientProtocol) -> None:
        """Initialize service with a GitHub client dependency."""
        self._github_client = github_client

    def commit_and_create_pr(
        self,
        branch_name: str,
        base_branch: str,
        changes: List[FileChange],
        commit_message: str,
        pr_title: str,
        pr_body: str,
    ) -> str:
        """Create a branch, commit changes, open a pull request, and return its URL."""
        if not changes:
            return ""

        self._github_client.create_branch(
            branch_name=branch_name, base_branch=base_branch
        )

        formatted_changes = [
            {
                "path": change.path,
                "action": change.action.value,
                "content": change.content,
            }
            for change in changes
        ]

        self._github_client.bulk_commit_changes(
            branch=branch_name, changes=formatted_changes, message=commit_message
        )

        pull_request = self._github_client.create_pull_request(
            head=branch_name,
            base=base_branch,
            title=pr_title,
            body=pr_body,
        )

        return pull_request.html_url
