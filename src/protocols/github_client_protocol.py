"""Protocol definition for GitHub client interface."""

from pathlib import Path
from typing import Optional, Protocol

from github import Github
from github.PullRequest import PullRequest


class GithubClientProtocol(Protocol):
    """Protocol for GitHub client operations."""

    def authenticate(self) -> Github:
        """
        Authenticate as GitHub App using private key and app ID.

        Returns:
            Authenticated GitHub API client.

        Raises:
            ValueError: If GitHub App credentials are not configured.
            FileNotFoundError: If private key file is not found.
            Exception: If authentication fails.
        """
        ...

    def clone_repository(self, target_path: Path, branch: str = "main") -> None:
        """
        Clone repository to local path using git commands with authentication.

        Args:
            target_path: Local directory path where repository will be cloned.
            branch: Branch name to checkout (default: "main").

        Raises:
            Exception: If cloning fails.
        """
        ...

    def create_branch(self, repo_path: Path, branch_name: str) -> None:
        """
        Create new git branch from the current branch.

        Args:
            repo_path: Path to the local git repository.
            branch_name: Name of the new branch to create.

        Raises:
            FileNotFoundError: If repository path doesn't exist.
            Exception: If branch creation fails.
        """
        ...

    def commit_and_push(self, repo_path: Path, branch_name: str, message: str) -> bool:
        """
        Stage all changes, commit, and push to remote branch.

        Args:
            repo_path: Path to the local git repository.
            branch_name: Name of the branch to push.
            message: Commit message.

        Returns:
            True if changes were committed and pushed, False if there were no changes.

        Raises:
            FileNotFoundError: If repository path doesn't exist.
            Exception: If commit or push fails.
        """
        ...

    def create_pull_request(
        self,
        repo_full_name: str,
        head_branch: str,
        title: str,
        body: str,
        base_branch: Optional[str] = None,
    ) -> PullRequest:
        """
        Create pull request via GitHub API.

        Args:
            repo_full_name: Full repository name (e.g., "owner/repo").
            head_branch: Name of the branch containing changes.
            title: Title of the pull request.
            body: Description/body of the pull request.
            base_branch: Base branch to merge into (default: from settings).

        Returns:
            PullRequest object with URL and other details.

        Raises:
            Exception: If PR creation fails.
        """
        ...

    def get_authenticated_clone_url(self, repo_full_name: str) -> str:
        """
        Get authenticated clone URL for the repository.

        Args:
            repo_full_name: Full repository name (e.g., "owner/repo").

        Returns:
            HTTPS clone URL with authentication token embedded.
        """
        ...
