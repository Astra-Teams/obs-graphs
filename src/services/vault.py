"""Service for managing Obsidian Vault operations via GitHub API and local copy."""

from pathlib import Path
from typing import List, Optional

from src.protocols import GithubClientProtocol, VaultServiceProtocol
from src.state import FileChange


class VaultService(VaultServiceProtocol):
    """Service for handling file operations within the Obsidian Vault."""

    def __init__(
        self,
        github_client: GithubClientProtocol,
        branch: str,
        vault_path: Optional[Path] = None,
    ):
        """Initialize the vault service."""
        self.github_client = github_client
        self.branch = branch
        self._vault_path = vault_path

    def set_vault_path(self, vault_path: Path) -> None:
        """Update the local vault path used for read-heavy operations."""
        self._vault_path = vault_path

    def get_file_content(self, path: str) -> str:
        """Return the content of a file from the repository via the GitHub API."""
        return self.github_client.get_file_content(path, self.branch)

    def update_file(self, path: str, content: str, message: str) -> None:
        """Update or create a file within the repository."""
        changes = [{"action": "update", "path": path, "content": content}]
        self.github_client.bulk_commit_changes(self.branch, changes, message)

    def list_files(self, path: str = "") -> List[str]:
        """List files from the repository tree via the GitHub API."""
        tree = self.github_client.get_tree(self.branch, recursive=True)
        return [
            element.path
            for element in tree.tree
            if element.type == "blob" and (not path or element.path.startswith(path))
        ]

    def apply_changes(self, changes: List[FileChange], message: str) -> str:
        """Apply file changes to the repository using a bulk commit."""
        if not changes:
            return ""

        bulk_changes = [
            {
                "path": change.path,
                "content": change.content,
                "action": change.action.value,
            }
            for change in changes
        ]

        return self.github_client.bulk_commit_changes(
            self.branch, bulk_changes, message
        )

    def get_vault_summary(self) -> dict:
        """Compute a summary of the vault using the local copy."""
        markdown_files = list(self._vault_path.rglob("*.md"))
        total_articles = len(markdown_files)

        categories = {
            path.relative_to(self._vault_path).parts[0]
            for path in markdown_files
            if path.relative_to(self._vault_path).parts
        }

        recent_files = sorted(
            markdown_files,
            key=lambda file_path: file_path.stat().st_mtime,
            reverse=True,
        )[:5]

        recent_updates = [
            str(file_path.relative_to(self._vault_path).as_posix())
            for file_path in recent_files
        ]

        return {
            "total_articles": total_articles,
            "categories": sorted(categories),
            "recent_updates": recent_updates,
        }
