"""Service for managing Obsidian Vault file operations via GitHub API."""

from typing import List

from src.protocols import GithubClientProtocol, VaultServiceProtocol
from src.state import FileChange


class VaultService(VaultServiceProtocol):
    """Service for handling file operations within the Obsidian Vault via GitHub API."""

    def __init__(self, github_client: GithubClientProtocol, branch: str):
        """
        Initialize the VaultService.

        Args:
            github_client: GitHub client for API operations.
            branch: Branch name to operate on.
        """
        self.github_client = github_client
        self.branch = branch

    def get_file_content(self, path: str) -> str:
        """
        Get file content from the vault.

        Args:
            path: Path to the file in the repository.

        Returns:
            File content as string.

        Raises:
            Exception: If file retrieval fails.
        """
        return self.github_client.get_file_content(path, self.branch)

    def update_file(self, path: str, content: str, message: str) -> None:
        """
        Update or create a file in the vault.

        Args:
            path: Path to the file in the repository.
            content: New file content.
            message: Commit message.

        Raises:
            Exception: If file update fails.
        """
        self.github_client.create_or_update_file(path, content, self.branch, message)

    def list_files(self, path: str = "") -> List[str]:
        """
        List files in the vault.

        Args:
            path: Optional path prefix to filter files (default: root).

        Returns:
            List of file paths.

        Raises:
            Exception: If file listing fails.
        """
        tree = self.github_client.get_tree(self.branch, recursive=True)

        # Filter for files (not trees/directories) and optionally by path prefix
        files = [
            element.path
            for element in tree.tree
            if element.type == "blob" and (not path or element.path.startswith(path))
        ]

        return files

    def apply_changes(self, changes: List[FileChange], message: str) -> str:
        """
        Apply a list of file changes to the vault via GitHub API using bulk commit.

        This method commits all changes atomically in a single commit, which is
        much more efficient than individual file operations.

        Args:
            changes: A list of FileChange objects representing the modifications.
            message: Commit message for all changes.

        Returns:
            SHA of the created commit.

        Raises:
            Exception: If applying changes fails.
        """
        if not changes:
            return ""

        # Convert FileChange objects to format expected by bulk_commit_changes
        bulk_changes = []
        for change in changes:
            bulk_changes.append(
                {
                    "path": change.path,
                    "content": change.content,
                    "action": change.action.value,  # Convert enum to string
                }
            )

        # Use bulk commit for atomic operation
        commit_sha = self.github_client.bulk_commit_changes(
            self.branch, bulk_changes, message
        )

        return commit_sha
