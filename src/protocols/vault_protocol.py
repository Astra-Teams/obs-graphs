"""Protocol definition for vault service interface."""

from pathlib import Path
from typing import List, Protocol

from src.state import FileChange, VaultSummary


class VaultServiceProtocol(Protocol):
    """Protocol for vault service operations."""

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
        ...

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
        ...

    def get_vault_summary(self, vault_path: Path) -> VaultSummary:
        """
        Return a summary of the vault including article count, categories, and metadata.

        Args:
            vault_path: The absolute path to the local vault.

        Returns:
            A VaultSummary object with statistics about the vault.
        """
        ...
