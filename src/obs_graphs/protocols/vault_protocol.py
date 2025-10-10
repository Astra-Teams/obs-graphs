"""Protocol definition for vault service interface."""

from pathlib import Path
from typing import List, Protocol

from src.obs_graphs.graphs.article_proposal.state import VaultSummary


class VaultServiceProtocol(Protocol):
    """Protocol for read-only vault service operations."""

    def set_vault_path(self, vault_path: Path) -> None:
        """Update the local vault path used for analysis."""
        ...

    def get_file_content(self, path: str) -> str:
        """Return the content of a vault file from the local filesystem."""
        ...

    def list_files(self, path: str = "") -> List[str]:
        """List vault files, optionally filtered by a relative path prefix."""
        ...

    def get_vault_summary(self) -> VaultSummary:
        """Return a summary of the vault including total articles and categories."""
        ...

    def validate_vault_structure(self, vault_path: Path) -> bool:
        """Validate that the vault structure is intact after changes."""
        ...
