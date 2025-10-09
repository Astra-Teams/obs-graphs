"""Protocol definition for vault service interface."""

from typing import List, Protocol

from src.state import FileChange, VaultSummary


class VaultServiceProtocol(Protocol):
    """Protocol for vault service operations."""

    def apply_changes(self, changes: List[FileChange], message: str) -> str:
        """Commit a list of changes to the repository and return the commit SHA."""
        ...

    def get_vault_summary(self) -> VaultSummary:
        """Return a summary of the vault including total articles and categories."""
        ...
