"""Protocol definition for vault service interface."""

from pathlib import Path
from typing import List, Protocol

from src.state import FileChange, VaultSummary


class VaultServiceProtocol(Protocol):
    """Protocol for vault service operations."""

    def apply_changes(self, vault_path: Path, changes: List[FileChange]) -> None:
        ...

    def validate_vault_structure(self, vault_path: Path) -> bool:
        ...

    def get_vault_summary(self, vault_path: Path) -> VaultSummary:
        ...

    def get_all_categories(self, vault_path: Path | None = None) -> List[str]:
        """Return a list of top-level category directories in the vault."""
        ...

    def get_concatenated_content_from_category(
        self, category_name: str, vault_path: Path | None = None
    ) -> str:
        """Return the combined markdown content for all files within a category."""
        ...
