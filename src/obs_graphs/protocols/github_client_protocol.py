"""Protocol definition for GitHub client interface."""

from typing import Protocol

from github import Github
from github.GitTree import GitTree
from github.PullRequest import PullRequest


class GithubClientProtocol(Protocol):
    """Protocol for GitHub client operations via API."""

    def authenticate(self) -> Github:
        """
        Authenticate using Personal Access Token.

        Returns:
            Authenticated GitHub API client.

        Raises:
            ValueError: If GitHub PAT is not configured.
        """
        ...

    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """
        Create new branch from base branch via GitHub API.

        Args:
            branch_name: Name of the new branch to create.
            base_branch: Base branch to create from (default: "main").

        Raises:
            Exception: If branch creation fails.
        """
        ...

    def get_file_content(self, path: str, branch: str) -> str:
        """
        Get file content from repository via GitHub API.

        Args:
            path: Path to the file in the repository.
            branch: Branch name to get the file from.

        Returns:
            File content as string.

        Raises:
            Exception: If file retrieval fails.
        """
        ...

    def create_or_update_file(
        self, path: str, content: str, branch: str, message: str
    ) -> None:
        """
        Create or update file in repository via GitHub API.

        Args:
            path: Path to the file in the repository.
            content: New file content.
            branch: Branch name to commit to.
            message: Commit message.

        Raises:
            Exception: If file creation/update fails.
        """
        ...

    def delete_file(self, path: str, branch: str, message: str) -> None:
        """
        Delete file from repository via GitHub API.

        Args:
            path: Path to the file in the repository.
            branch: Branch name to delete from.
            message: Commit message.

        Raises:
            Exception: If file deletion fails.
        """
        ...

    def create_pull_request(
        self, head: str, base: str, title: str, body: str
    ) -> PullRequest:
        """
        Create pull request via GitHub API.

        Args:
            head: Name of the branch containing changes.
            base: Base branch to merge into.
            title: Title of the pull request.
            body: Description/body of the pull request.

        Returns:
            PullRequest object with URL and other details.

        Raises:
            Exception: If PR creation fails.
        """
        ...

    def get_tree(self, branch: str, recursive: bool = False) -> GitTree:
        """
        Get repository tree (file list) via GitHub API.

        Args:
            branch: Branch name to get the tree from.
            recursive: Whether to get the tree recursively (default: False).

        Returns:
            GitTree object containing file information.

        Raises:
            Exception: If tree retrieval fails.
        """
        ...

    def bulk_commit_changes(self, branch: str, changes: list, message: str) -> str:
        """Commit multiple file changes atomically and return the commit SHA."""
        ...
