"""Unit tests for the VaultService."""

from pathlib import Path

import pytest

from src.services import VaultService
from src.state import FileAction, FileChange, VaultSummary


@pytest.fixture
def vault_service():
    """Return a VaultService instance."""
    return VaultService()


def test_get_vault_summary(vault_service: VaultService, tmp_path: Path):
    """Test that get_vault_summary returns an accurate summary of the vault."""
    # Arrange
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / "Category 1").mkdir()
    (tmp_path / "Category 2").mkdir()
    (tmp_path / "file1.md").write_text("content1")
    (tmp_path / "Category 1" / "file2.md").write_text("content2")

    # Act
    summary = vault_service.get_vault_summary(tmp_path)

    # Assert
    assert isinstance(summary, VaultSummary)
    assert summary.total_articles == 2
    assert set(summary.categories) == {"Category 1", "Category 2"}
    assert len(summary.recent_updates) == 2


def test_apply_changes_create(vault_service: VaultService, tmp_path: Path):
    """Test that apply_changes correctly creates a new file."""
    # Arrange
    change = FileChange(
        path="new_file.md", action=FileAction.CREATE, content="new content"
    )

    # Act
    vault_service.apply_changes(tmp_path, [change])

    # Assert
    new_file = tmp_path / "new_file.md"
    assert new_file.exists()
    assert new_file.read_text() == "new content"


def test_apply_changes_update(vault_service: VaultService, tmp_path: Path):
    """Test that apply_changes correctly updates an existing file."""
    # Arrange
    (tmp_path / "existing_file.md").write_text("old content")
    change = FileChange(
        path="existing_file.md", action=FileAction.UPDATE, content="new content"
    )

    # Act
    vault_service.apply_changes(tmp_path, [change])

    # Assert
    existing_file = tmp_path / "existing_file.md"
    assert existing_file.exists()
    assert existing_file.read_text() == "new content"


def test_apply_changes_delete(vault_service: VaultService, tmp_path: Path):
    """Test that apply_changes correctly deletes a file."""
    # Arrange
    (tmp_path / "file_to_delete.md").write_text("content")
    change = FileChange(path="file_to_delete.md", action=FileAction.DELETE)

    # Act
    vault_service.apply_changes(tmp_path, [change])

    # Assert
    assert not (tmp_path / "file_to_delete.md").exists()


def test_validate_vault_structure(vault_service: VaultService, tmp_path: Path):
    """Test that validate_vault_structure correctly identifies valid and invalid vaults."""
    # Arrange
    assert not vault_service.validate_vault_structure(tmp_path)
    (tmp_path / ".obsidian").mkdir()

    # Act & Assert
    assert vault_service.validate_vault_structure(tmp_path)
