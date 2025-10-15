"""Service for managing read-only operations on the local Obsidian Vault."""

from pathlib import Path
from typing import List, Optional

from src.obs_glx.graphs.article_proposal.state import VaultSummary
from src.obs_glx.protocols import VaultServiceProtocol


class VaultService(VaultServiceProtocol):
    """Service for handling read-only file operations within the Obsidian Vault."""

    def __init__(self, vault_path: Optional[Path] = None) -> None:
        """Initialize the vault service."""
        self._vault_path = vault_path.resolve() if vault_path else None

    def set_vault_path(self, vault_path: Path) -> None:
        """Update the local vault path used for read-heavy operations."""
        self._vault_path = vault_path.resolve()

    def get_file_content(self, path: str) -> str:
        """Return the content of a file from the local vault copy."""
        vault_path = self._require_vault_path()
        target_path = (vault_path / path).resolve()

        if not target_path.is_relative_to(vault_path):
            raise ValueError(f"Path '{path}' escapes the configured vault root")

        if not target_path.is_file():
            raise FileNotFoundError(f"File not found in vault: {path}")

        return target_path.read_text(encoding="utf-8")

    def list_files(self, path: str = "") -> List[str]:
        """List files from the local vault copy."""
        vault_path = self._require_vault_path()
        prefix = path.lstrip("/")

        files: List[str] = []
        for file_path in vault_path.rglob("*"):
            if not file_path.is_file():
                continue

            relative = file_path.relative_to(vault_path).as_posix()
            if prefix and not relative.startswith(prefix):
                continue
            files.append(relative)

        return sorted(files)

    def get_vault_summary(self) -> VaultSummary:
        """Compute a summary of the vault using the local copy."""
        vault_path = self._require_vault_path()
        markdown_files = list(vault_path.rglob("*.md"))
        total_articles = len(markdown_files)

        return VaultSummary(
            total_articles=total_articles,
        )

    def validate_vault_structure(self, vault_path: Path) -> bool:
        """Validate that the vault structure is intact after changes."""
        if not vault_path.exists():
            return False

        # Check for at least some markdown files
        markdown_files = list(vault_path.rglob("*.md"))
        return len(markdown_files) > 0

    def _require_vault_path(self) -> Path:
        """Return the configured vault path or raise if it is missing."""
        if self._vault_path is None:
            raise ValueError(
                "Vault path is not configured. Call set_vault_path() before using read operations."
            )

        return self._vault_path
