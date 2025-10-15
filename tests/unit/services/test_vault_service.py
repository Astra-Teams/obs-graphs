"""Tests for the read-only VaultService."""

from pathlib import Path

import pytest

from src.obs_graphs.services import VaultService


@pytest.fixture
def vault_path(tmp_path: Path) -> Path:
    """Create a temporary vault directory with sample markdown files."""
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    (articles_dir / "first.md").write_text("# First", encoding="utf-8")

    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "second.md").write_text("# Second", encoding="utf-8")

    return tmp_path


@pytest.fixture
def vault_service(vault_path: Path) -> VaultService:
    """Return a VaultService configured with the temporary vault path."""
    return VaultService(vault_path)


def test_get_file_content_reads_local_file(vault_service: VaultService) -> None:
    """VaultService should read file contents from the local filesystem."""
    content = vault_service.get_file_content("articles/first.md")
    assert content == "# First"


def test_get_file_content_rejects_outside_paths(vault_service: VaultService) -> None:
    """Accessing paths outside the vault should raise an error."""
    with pytest.raises(ValueError):
        vault_service.get_file_content("../outside.md")


def test_list_files_returns_sorted_paths(vault_service: VaultService) -> None:
    """list_files should enumerate files relative to the vault root."""
    files = vault_service.list_files()
    assert files == ["articles/first.md", "notes/second.md"]


def test_list_files_filters_by_prefix(vault_service: VaultService) -> None:
    """list_files should filter results when a prefix is supplied."""
    files = vault_service.list_files("articles/")
    assert files == ["articles/first.md"]


def test_get_vault_summary_counts_files(vault_service: VaultService) -> None:
    """Vault summary should count markdown files correctly."""
    summary = vault_service.get_vault_summary()
    assert summary.total_articles == 2


def test_validate_vault_structure(vault_path: Path) -> None:
    """validate_vault_structure should verify vault directories containing markdown."""
    assert VaultService().validate_vault_structure(vault_path) is True
    assert VaultService().validate_vault_structure(vault_path / "missing") is False
