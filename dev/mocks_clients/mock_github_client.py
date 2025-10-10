"""Mock GitHub client for offline development and testing."""

from pathlib import Path
from unittest.mock import MagicMock

from github import Github
from github.PullRequest import PullRequest

from src.obs_graphs.protocols import GithubClientProtocol


class MockGithubClient(GithubClientProtocol):
    """
    Mock implementation of GitHub client for offline development.

    This mock client logs operations to console and returns dummy objects,
    allowing development without network connection or GitHub API credentials.
    """

    def authenticate(self) -> Github:
        """
        Mock authentication - returns a MagicMock object.

        Returns:
            Mock GitHub API client.
        """
        print("[MockGithubClient] authenticate() called - returning mock Github client")
        return MagicMock(spec=Github)

    def clone_repository(self, target_path: Path, branch: str = "main") -> None:
        """
        Mock repository cloning - logs operation without actual cloning.

        Args:
            target_path: Local directory path where repository would be cloned.
            branch: Branch name to checkout (default: "main").
        """
        print(
            f"[MockGithubClient] clone_repository(target_path={target_path}, branch={branch}) called - no actual cloning performed"
        )

    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """
        Mock branch creation - logs operation without actual branch creation.

        Args:
            branch_name: Name of the new branch to create.
            base_branch: Base branch to create from (default: "main").
        """
        print(
            f"[MockGithubClient] create_branch(branch_name={branch_name}, base_branch={base_branch}) called - no actual branch created"
        )

    def commit_and_push(self, repo_path: Path, branch_name: str, message: str) -> bool:
        """
        Mock commit and push - logs operation and returns True.

        Args:
            repo_path: Path to the local git repository.
            branch_name: Name of the branch to push.
            message: Commit message.

        Returns:
            Always returns True (simulating successful commit).
        """
        print(
            f"[MockGithubClient] commit_and_push(repo_path={repo_path}, branch_name={branch_name}, message={message}) called - returning True"
        )
        return True

    def create_pull_request(
        self, head: str, base: str, title: str, body: str
    ) -> PullRequest:
        """
        Mock PR creation - logs operation and returns mock PullRequest.

        Args:
            head: Name of the branch containing changes.
            base: Base branch to merge into.
            title: Title of the pull request.
            body: Description/body of the pull request.

        Returns:
            Mock PullRequest object.
        """
        print(
            f"[MockGithubClient] create_pull_request(head={head}, base={base}, title={title}) called - returning mock PR"
        )
        mock_pr = MagicMock(spec=PullRequest)
        mock_pr.html_url = "https://github.com/mock-repo/pull/1"
        mock_pr.number = 1
        mock_pr.title = title
        return mock_pr

    def get_authenticated_clone_url(self, repo_full_name: str) -> str:
        """
        Mock authenticated clone URL - returns dummy URL.

        Args:
            repo_full_name: Full repository name (e.g., "owner/repo").

        Returns:
            Dummy HTTPS clone URL.
        """
        print(
            f"[MockGithubClient] get_authenticated_clone_url(repo={repo_full_name}) called - returning mock URL"
        )
        return f"https://mock-token@github.com/{repo_full_name}.git"

    def bulk_commit_changes(self, branch: str, changes: list, message: str) -> str:
        """
        Mock bulk commit changes - logs operation and returns mock SHA.

        Args:
            branch: Branch name to commit to.
            changes: List of dicts with 'path', 'content', 'action'.
            message: Commit message.

        Returns:
            Mock commit SHA.
        """
        print(
            f"[MockGithubClient] bulk_commit_changes(branch={branch}, changes={len(changes)}, message={message[:50]}...) called - returning mock SHA"
        )
        return "mock-commit-sha-1234567890abcdef"
