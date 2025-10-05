"""Service for managing Obsidian Vault file operations."""

from pathlib import Path
from typing import List

from src.protocols import VaultServiceProtocol
from src.state import FileAction, FileChange, VaultSummary


class VaultService(VaultServiceProtocol):
    """Service for handling file operations within the Obsidian Vault."""

    def apply_changes(self, vault_path: Path, changes: List[FileChange]) -> None:
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
        return (vault_path / ".obsidian").is_dir()

    def get_vault_summary(self, vault_path: Path) -> VaultSummary:
        all_files = list(vault_path.glob("**/*.md"))
        total_articles = len(all_files)

        categories = [
            d.name
            for d in vault_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        sorted_files = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)
        recent_updates = [str(f.relative_to(vault_path)) for f in sorted_files[:5]]

        return VaultSummary(
            total_articles=total_articles,
            categories=categories,
            recent_updates=recent_updates,
        )

    def get_all_categories(self, vault_path: Path | None = None) -> List[str]:
        base_path = self._resolve_vault_path(vault_path)
        return [
            entry.name
            for entry in base_path.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        ]

    def get_concatenated_content_from_category(
        self, category_name: str, vault_path: Path | None = None
    ) -> str:
        base_path = self._resolve_vault_path(vault_path)
        category_path = base_path / category_name
        if not category_path.exists() or not category_path.is_dir():
            return ""

        contents: List[str] = []
        for markdown_file in category_path.rglob("*.md"):
            contents.append(markdown_file.read_text(encoding="utf-8"))
        return "\n\n".join(contents)

    def _resolve_vault_path(self, vault_path: Path | None) -> Path:
        if vault_path is None:
            raise ValueError("Vault path must be provided for this operation")
        return vault_path
