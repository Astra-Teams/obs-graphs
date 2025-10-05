"""Vault scanning utilities mixin for agents."""

from pathlib import Path
from typing import List, Optional


class VaultScanMixin:
    """
    Mixin providing common vault scanning utilities.

    Provides methods for scanning markdown files in a vault.
    """

    def _scan_markdown_files(
        self, vault_path: Path, recursive: bool = True
    ) -> List[Path]:
        """
        Scan vault for markdown files.

        Args:
            vault_path: Path to the vault
            recursive: If True, scan recursively (default), else only top level

        Returns:
            List of Path objects for markdown files
        """
        if recursive:
            return sorted([p for p in vault_path.rglob("*.md") if p.is_file()])
        else:
            return sorted([p for p in vault_path.glob("*.md") if p.is_file()])

    def _read_file_safe(self, path: Path) -> Optional[str]:
        """
        Safely read a file's content.

        Args:
            path: Path to the file

        Returns:
            File content as string, or None if read fails
        """
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def _get_relative_path(self, file_path: Path, vault_path: Path) -> str:
        """
        Get relative path from vault root.

        Args:
            file_path: Absolute path to the file
            vault_path: Vault root path

        Returns:
            Relative path as POSIX string
        """
        return file_path.relative_to(vault_path).as_posix()
