"""Service for managing Obsidian Vault file operations."""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.agents.base import FileAction, FileChange


@dataclass
class VaultSummary:
    """
    Dataclass representing a summary of the vault's state.

    Attributes:
        total_articles: Total number of markdown files in the vault.
        categories: List of top-level directories representing categories.
        recent_updates: List of recently modified files.
    """

    total_articles: int
    categories: List[str]
    recent_updates: List[str]


class VaultService:
    """Service for handling file operations within the Obsidian Vault."""

    def apply_changes(self, vault_path: Path, changes: List[FileChange]) -> None:
        """
        Apply a list of file changes to the local vault clone.

        Args:
            vault_path: The absolute path to the local vault.
            changes: A list of FileChange objects representing the modifications.

        Raises:
            FileNotFoundError: If a file to be updated or deleted does not exist.
            FileExistsError: If a file to be created already exists.
        """
        for change in changes:
            file_path = vault_path / change.path

            if change.action == FileAction.CREATE:
                if file_path.exists():
                    raise FileExistsError(f"File already exists at {file_path}")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(change.content or "", encoding="utf-8")

            elif change.action == FileAction.UPDATE:
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found at {file_path}")
                file_path.write_text(change.content or "", encoding="utf-8")

            elif change.action == FileAction.DELETE:
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found at {file_path}")
                file_path.unlink()

    def validate_vault_structure(self, vault_path: Path) -> bool:
        """
        Ensure the vault is in a valid state before and after changes.

        This can be extended to check for broken links, empty files, or other
        inconsistencies.

        Args:
            vault_path: The absolute path to the local vault.

        Returns:
            True if the vault structure is valid, False otherwise.
        """
        # Placeholder validation: Check if .obsidian directory exists
        return (vault_path / ".obsidian").is_dir()

    def get_vault_summary(self, vault_path: Path) -> VaultSummary:
        """
        Return a summary of the vault including article count, categories, and metadata.

        Args:
            vault_path: The absolute path to the local vault.

        Returns:
            A VaultSummary object with statistics about the vault.
        """
        all_files = list(vault_path.glob("**/*.md"))
        total_articles = len(all_files)

        categories = [
            d.name
            for d in vault_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        # Get 5 most recently modified markdown files
        sorted_files = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)
        recent_updates = [str(f.relative_to(vault_path)) for f in sorted_files[:5]]

        return VaultSummary(
            total_articles=total_articles,
            categories=categories,
            recent_updates=recent_updates,
        )
