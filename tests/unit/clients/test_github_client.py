"""Unit tests for the GithubClient."""

from unittest.mock import MagicMock, patch

import pytest

from src.obs_graphs.clients import GithubClient
from src.obs_graphs.config import ObsGraphsSettings


@pytest.fixture
def github_client():
    """Return a GithubClient instance with mocked credentials."""
    settings = ObsGraphsSettings(
        OBSIDIAN_VAULT_GITHUB_TOKEN="fake-pat",
        OBSIDIAN_VAULT_REPOSITORY="user/repo",
        VAULT_GITHUB_API_TIMEOUT_SECONDS=30,
    )
    return GithubClient(settings)


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_create_branch(mock_authenticate, github_client: GithubClient):
    """Test that create_branch calls the GitHub API with correct parameters."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_base_ref = MagicMock()
    mock_base_ref.object.sha = "abc123"

    mock_github.get_repo.return_value = mock_repo
    mock_repo.get_git_ref.return_value = mock_base_ref
    mock_authenticate.return_value = mock_github

    # Act
    github_client.create_branch("new-branch", "main")

    # Assert
    mock_authenticate.assert_called_once()
    mock_github.get_repo.assert_called_once_with("user/repo")
    mock_repo.get_git_ref.assert_called_once_with("heads/main")
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/new-branch", sha="abc123"
    )


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_get_file_content(mock_authenticate, github_client: GithubClient):
    """Test that get_file_content retrieves file content via API."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_file = MagicMock()
    mock_file.decoded_content = b"file content here"

    mock_github.get_repo.return_value = mock_repo
    mock_repo.get_contents.return_value = mock_file
    mock_authenticate.return_value = mock_github

    # Act
    content = github_client.get_file_content("path/to/file.md", "main")

    # Assert
    assert content == "file content here"
    mock_authenticate.assert_called_once()
    mock_github.get_repo.assert_called_once_with("user/repo")
    mock_repo.get_contents.assert_called_once_with("path/to/file.md", ref="main")


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_bulk_commit_changes_create_only(
    mock_authenticate, github_client: GithubClient
):
    """Test bulk_commit_changes with create operations only."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_branch_ref = MagicMock()
    mock_branch_ref.object.sha = "base-commit-sha"
    mock_base_commit = MagicMock()
    mock_base_commit.tree.sha = "base-tree-sha"
    mock_base_tree = MagicMock()
    mock_base_tree.tree = []  # No existing files
    mock_new_tree = MagicMock()
    mock_new_tree.sha = "new-tree-sha"
    mock_new_commit = MagicMock()
    mock_new_commit.sha = "new-commit-sha"
    mock_blob = MagicMock()
    mock_blob.sha = "blob-sha"

    mock_repo.get_git_ref.return_value = mock_branch_ref
    mock_repo.get_git_commit.return_value = mock_base_commit
    mock_repo.get_git_tree.return_value = mock_base_tree
    mock_repo.create_git_blob.return_value = mock_blob
    mock_repo.create_git_tree.return_value = mock_new_tree
    mock_repo.create_git_commit.return_value = mock_new_commit
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    changes = [{"action": "create", "path": "new/file.md", "content": "new content"}]

    # Act
    result = github_client.bulk_commit_changes("main", changes, "Create file")

    # Assert
    assert result == "new-commit-sha"
    mock_repo.get_git_tree.assert_called_once_with("base-tree-sha", recursive=True)
    mock_repo.create_git_blob.assert_called_once_with("new content", "utf-8")
    mock_repo.create_git_tree.assert_called_once()
    mock_repo.create_git_commit.assert_called_once_with(
        message="Create file", tree=mock_new_tree, parents=[mock_base_commit]
    )
    mock_branch_ref.edit.assert_called_once_with(sha="new-commit-sha", force=False)


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_bulk_commit_changes_update_only(
    mock_authenticate, github_client: GithubClient
):
    """Test bulk_commit_changes with update operations only."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_branch_ref = MagicMock()
    mock_branch_ref.object.sha = "base-commit-sha"
    mock_base_commit = MagicMock()
    mock_base_commit.tree.sha = "base-tree-sha"
    mock_base_tree = MagicMock()
    mock_element = MagicMock()
    mock_element.path = "other/file.md"
    mock_element.type = "blob"
    mock_element.mode = "100644"
    mock_element.sha = "element-sha"
    mock_base_tree.tree = [mock_element]
    mock_new_tree = MagicMock()
    mock_new_tree.sha = "new-tree-sha"
    mock_new_commit = MagicMock()
    mock_new_commit.sha = "new-commit-sha"
    mock_blob = MagicMock()
    mock_blob.sha = "blob-sha"

    mock_repo.get_git_ref.return_value = mock_branch_ref
    mock_repo.get_git_commit.return_value = mock_base_commit
    mock_repo.get_git_tree.return_value = mock_base_tree
    mock_repo.create_git_blob.return_value = mock_blob
    mock_repo.create_git_tree.return_value = mock_new_tree
    mock_repo.create_git_commit.return_value = mock_new_commit
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    changes = [
        {"action": "update", "path": "existing/file.md", "content": "updated content"}
    ]

    # Act
    result = github_client.bulk_commit_changes("main", changes, "Update file")

    # Assert
    assert result == "new-commit-sha"
    mock_repo.get_git_tree.assert_called_once_with("base-tree-sha", recursive=True)
    mock_repo.create_git_blob.assert_called_once_with("updated content", "utf-8")
    mock_repo.create_git_tree.assert_called_once()
    created_tree_elements = mock_repo.create_git_tree.call_args[0][0]
    # Check that the updated file is in the new tree
    assert any(elem["path"] == "existing/file.md" for elem in created_tree_elements)
    # Check that the other file is preserved
    assert any(elem["path"] == "other/file.md" for elem in created_tree_elements)


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_bulk_commit_changes_delete_only(
    mock_authenticate, github_client: GithubClient
):
    """Test bulk_commit_changes with delete operations only."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_branch_ref = MagicMock()
    mock_branch_ref.object.sha = "base-commit-sha"
    mock_base_commit = MagicMock()
    mock_base_commit.tree.sha = "base-tree-sha"
    mock_base_tree = MagicMock()
    mock_element1 = MagicMock()
    mock_element1.path = "other/file.md"
    mock_element1.type = "blob"
    mock_element1.mode = "100644"
    mock_element1.sha = "element-sha"
    mock_element2 = MagicMock()
    mock_element2.path = "delete/file.md"
    mock_element2.type = "blob"
    mock_element2.mode = "100644"
    mock_element2.sha = "delete-sha"
    mock_base_tree.tree = [mock_element1, mock_element2]
    mock_new_tree = MagicMock()
    mock_new_tree.sha = "new-tree-sha"
    mock_new_commit = MagicMock()
    mock_new_commit.sha = "new-commit-sha"

    mock_repo.get_git_ref.return_value = mock_branch_ref
    mock_repo.get_git_commit.return_value = mock_base_commit
    mock_repo.get_git_tree.return_value = mock_base_tree
    mock_repo.create_git_tree.return_value = mock_new_tree
    mock_repo.create_git_commit.return_value = mock_new_commit
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    changes = [{"action": "delete", "path": "delete/file.md"}]

    # Act
    result = github_client.bulk_commit_changes("main", changes, "Delete file")

    # Assert
    assert result == "new-commit-sha"
    mock_repo.get_git_tree.assert_called_once_with("base-tree-sha", recursive=True)
    mock_repo.create_git_tree.assert_called_once()
    created_tree_elements = mock_repo.create_git_tree.call_args[0][0]
    # Check that the preserved file is in the new tree
    assert any(elem["path"] == "other/file.md" for elem in created_tree_elements)
    # Check that the deleted file is NOT in the new tree
    assert not any(elem["path"] == "delete/file.md" for elem in created_tree_elements)


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_bulk_commit_changes_mixed_operations(
    mock_authenticate, github_client: GithubClient
):
    """Test bulk_commit_changes with mixed create, update, and delete operations."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_branch_ref = MagicMock()
    mock_branch_ref.object.sha = "base-commit-sha"
    mock_base_commit = MagicMock()
    mock_base_commit.tree.sha = "base-tree-sha"
    mock_base_tree = MagicMock()
    mock_element = MagicMock()
    mock_element.path = "existing/file.md"
    mock_element.type = "blob"
    mock_element.mode = "100644"
    mock_element.sha = "element-sha"
    mock_base_tree.tree = [mock_element]
    mock_new_tree = MagicMock()
    mock_new_tree.sha = "new-tree-sha"
    mock_new_commit = MagicMock()
    mock_new_commit.sha = "new-commit-sha"
    mock_blob1 = MagicMock()
    mock_blob1.sha = "blob1-sha"
    mock_blob2 = MagicMock()
    mock_blob2.sha = "blob2-sha"

    mock_repo.get_git_ref.return_value = mock_branch_ref
    mock_repo.get_git_commit.return_value = mock_base_commit
    mock_repo.get_git_tree.return_value = mock_base_tree
    mock_repo.create_git_blob.side_effect = [mock_blob1, mock_blob2]
    mock_repo.create_git_tree.return_value = mock_new_tree
    mock_repo.create_git_commit.return_value = mock_new_commit
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    changes = [
        {"action": "create", "path": "new/file.md", "content": "new content"},
        {"action": "update", "path": "existing/file.md", "content": "updated content"},
        {"action": "delete", "path": "delete/file.md"},
    ]

    # Act
    result = github_client.bulk_commit_changes("main", changes, "Mixed changes")

    # Assert
    assert result == "new-commit-sha"
    mock_repo.get_git_tree.assert_called_once_with("base-tree-sha", recursive=True)
    assert mock_repo.create_git_blob.call_count == 2


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_bulk_commit_changes_empty_list(mock_authenticate, github_client: GithubClient):
    """Test bulk_commit_changes with empty changes list."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_branch_ref = MagicMock()
    mock_branch_ref.object.sha = "base-commit-sha"

    mock_repo.get_git_ref.return_value = mock_branch_ref
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    changes = []

    # Act
    result = github_client.bulk_commit_changes("main", changes, "No changes")

    # Assert
    assert result == "base-commit-sha"  # Should return base commit SHA
    mock_repo.create_git_blob.assert_not_called()
    mock_repo.create_git_tree.assert_not_called()
    mock_repo.create_git_commit.assert_not_called()
    mock_branch_ref.edit.assert_not_called()


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_create_pull_request(mock_authenticate, github_client: GithubClient):
    """Test that create_pull_request calls the GitHub API with correct parameters."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/user/repo/pull/1"

    mock_repo.create_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    # Act
    pr = github_client.create_pull_request(
        head="new-branch", base="main", title="Test PR", body="This is a test PR."
    )

    # Assert
    assert pr.html_url == "https://github.com/user/repo/pull/1"
    mock_authenticate.assert_called_once()
    mock_github.get_repo.assert_called_once_with("user/repo")
    mock_repo.create_pull.assert_called_once_with(
        title="Test PR", body="This is a test PR.", head="new-branch", base="main"
    )


@patch("src.obs_graphs.clients.github_client.GithubClient.authenticate")
def test_get_tree(mock_authenticate, github_client: GithubClient):
    """Test that get_tree retrieves repository tree via API."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_branch_ref = MagicMock()
    mock_branch_ref.object.sha = "commit-sha"
    mock_commit = MagicMock()
    mock_commit.tree.sha = "tree-sha"
    mock_tree = MagicMock()

    mock_repo.get_git_ref.return_value = mock_branch_ref
    mock_repo.get_git_commit.return_value = mock_commit
    mock_repo.get_git_tree.return_value = mock_tree
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    # Act
    tree = github_client.get_tree("main", recursive=True)

    # Assert
    assert tree == mock_tree
    mock_authenticate.assert_called_once()
    mock_repo.get_git_ref.assert_called_once_with("heads/main")
    mock_repo.get_git_commit.assert_called_once_with("commit-sha")
    mock_repo.get_git_tree.assert_called_once_with("tree-sha", recursive=True)
