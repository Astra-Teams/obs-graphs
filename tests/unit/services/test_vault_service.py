"""Unit tests for the VaultService."""

from unittest.mock import MagicMock

import pytest

from src.services import VaultService
from src.state import FileAction, FileChange


@pytest.fixture
def mock_github_client():
    """Return a mock GitHub client."""
    return MagicMock()


@pytest.fixture
def vault_service(mock_github_client):
    """Return a VaultService instance with mocked GitHub client."""
    return VaultService(mock_github_client, "test-branch")


def test_get_file_content(vault_service: VaultService, mock_github_client):
    """Test that get_file_content calls github_client.get_file_content."""
    # Arrange
    mock_github_client.get_file_content.return_value = "file content"

    # Act
    content = vault_service.get_file_content("path/to/file.md")

    # Assert
    assert content == "file content"
    mock_github_client.get_file_content.assert_called_once_with(
        "path/to/file.md", "test-branch"
    )


def test_update_file(vault_service: VaultService, mock_github_client):
    """Test that update_file calls github_client.create_or_update_file."""
    # Act
    vault_service.update_file("path/to/file.md", "new content", "Update message")

    # Assert
    mock_github_client.create_or_update_file.assert_called_once_with(
        "path/to/file.md", "new content", "test-branch", "Update message"
    )


def test_list_files(vault_service: VaultService, mock_github_client):
    """Test that list_files retrieves and filters files from tree."""
    # Arrange
    mock_tree = MagicMock()
    mock_element1 = MagicMock()
    mock_element1.type = "blob"
    mock_element1.path = "file1.md"

    mock_element2 = MagicMock()
    mock_element2.type = "blob"
    mock_element2.path = "dir/file2.md"

    mock_element3 = MagicMock()
    mock_element3.type = "tree"
    mock_element3.path = "dir"

    mock_tree.tree = [mock_element1, mock_element2, mock_element3]
    mock_github_client.get_tree.return_value = mock_tree

    # Act
    files = vault_service.list_files()

    # Assert
    assert files == ["file1.md", "dir/file2.md"]
    mock_github_client.get_tree.assert_called_once_with("test-branch", recursive=True)


def test_list_files_with_path_filter(vault_service: VaultService, mock_github_client):
    """Test that list_files filters by path prefix."""
    # Arrange
    mock_tree = MagicMock()
    mock_element1 = MagicMock()
    mock_element1.type = "blob"
    mock_element1.path = "articles/file1.md"

    mock_element2 = MagicMock()
    mock_element2.type = "blob"
    mock_element2.path = "notes/file2.md"

    mock_tree.tree = [mock_element1, mock_element2]
    mock_github_client.get_tree.return_value = mock_tree

    # Act
    files = vault_service.list_files("articles/")

    # Assert
    assert files == ["articles/file1.md"]


def test_apply_changes_create(vault_service: VaultService, mock_github_client):
    """Test that apply_changes correctly creates a new file."""
    # Arrange
    change = FileChange(
        path="new_file.md", action=FileAction.CREATE, content="new content"
    )
    mock_github_client.bulk_commit_changes.return_value = "abc123"

    # Act
    commit_sha = vault_service.apply_changes([change], "Test commit message")

    # Assert
    assert commit_sha == "abc123"
    mock_github_client.bulk_commit_changes.assert_called_once()
    call_args = mock_github_client.bulk_commit_changes.call_args
    assert call_args[0][0] == "test-branch"
    assert len(call_args[0][1]) == 1
    assert call_args[0][1][0]["path"] == "new_file.md"
    assert call_args[0][2] == "Test commit message"


def test_apply_changes_update(vault_service: VaultService, mock_github_client):
    """Test that apply_changes correctly updates an existing file."""
    # Arrange
    change = FileChange(
        path="existing_file.md", action=FileAction.UPDATE, content="updated content"
    )
    mock_github_client.bulk_commit_changes.return_value = "def456"

    # Act
    commit_sha = vault_service.apply_changes([change], "Update file")

    # Assert
    assert commit_sha == "def456"
    mock_github_client.bulk_commit_changes.assert_called_once()


def test_apply_changes_delete(vault_service: VaultService, mock_github_client):
    """Test that apply_changes correctly deletes a file."""
    # Arrange
    change = FileChange(path="file_to_delete.md", action=FileAction.DELETE)
    mock_github_client.bulk_commit_changes.return_value = "ghi789"

    # Act
    commit_sha = vault_service.apply_changes([change], "Delete file")

    # Assert
    assert commit_sha == "ghi789"
    mock_github_client.bulk_commit_changes.assert_called_once()


def test_apply_changes_multiple(vault_service: VaultService, mock_github_client):
    """Test that apply_changes processes multiple changes atomically."""
    # Arrange
    changes = [
        FileChange(path="file1.md", action=FileAction.CREATE, content="content1"),
        FileChange(path="file2.md", action=FileAction.UPDATE, content="content2"),
        FileChange(path="file3.md", action=FileAction.DELETE),
    ]
    mock_github_client.bulk_commit_changes.return_value = "jkl012"

    # Act
    commit_sha = vault_service.apply_changes(changes, "Multiple changes")

    # Assert
    assert commit_sha == "jkl012"
    # Should be a single bulk commit, not multiple calls
    mock_github_client.bulk_commit_changes.assert_called_once()
    call_args = mock_github_client.bulk_commit_changes.call_args
    assert len(call_args[0][1]) == 3  # 3 changes in one commit
