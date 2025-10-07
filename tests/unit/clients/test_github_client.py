"""Unit tests for the GithubClient."""

from unittest.mock import MagicMock, patch

import pytest

from src.clients import GithubClient
from src.settings import get_settings


@pytest.fixture
def github_client(monkeypatch):
    """Return a GithubClient instance with mocked credentials."""
    # Clear settings cache before setting env vars
    get_settings.cache_clear()

    monkeypatch.setenv("VAULT_GITHUB_TOKEN", "fake-pat")
    monkeypatch.setenv("OBSIDIAN_VAULT_REPO_FULL_NAME", "user/repo")
    monkeypatch.setenv("GITHUB_API_TIMEOUT_SECONDS", "30")
    settings = get_settings()
    return GithubClient(settings)


@patch("src.clients.github_client.GithubClient.authenticate")
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


@patch("src.clients.github_client.GithubClient.authenticate")
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


@patch("src.clients.github_client.GithubClient.authenticate")
def test_create_or_update_file_create(mock_authenticate, github_client: GithubClient):
    """Test that create_or_update_file creates a new file when it doesn't exist."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()

    # Simulate file not found
    from github import GithubException

    mock_repo.get_contents.side_effect = GithubException(
        404, {"message": "Not Found"}, None
    )

    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    # Act
    github_client.create_or_update_file(
        "new/file.md", "new content", "main", "Create file"
    )

    # Assert
    mock_authenticate.assert_called_once()
    mock_repo.create_file.assert_called_once_with(
        path="new/file.md", message="Create file", content="new content", branch="main"
    )


@patch("src.clients.github_client.GithubClient.authenticate")
def test_create_or_update_file_update(mock_authenticate, github_client: GithubClient):
    """Test that create_or_update_file updates an existing file."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_existing_file = MagicMock()
    mock_existing_file.sha = "existing-sha"

    mock_repo.get_contents.return_value = mock_existing_file
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    # Act
    github_client.create_or_update_file(
        "existing/file.md", "updated content", "main", "Update file"
    )

    # Assert
    mock_authenticate.assert_called_once()
    mock_repo.update_file.assert_called_once_with(
        path="existing/file.md",
        message="Update file",
        content="updated content",
        sha="existing-sha",
        branch="main",
    )


@patch("src.clients.github_client.GithubClient.authenticate")
def test_delete_file(mock_authenticate, github_client: GithubClient):
    """Test that delete_file deletes a file via API."""
    # Arrange
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_file = MagicMock()
    mock_file.sha = "file-sha"

    mock_repo.get_contents.return_value = mock_file
    mock_github.get_repo.return_value = mock_repo
    mock_authenticate.return_value = mock_github

    # Act
    github_client.delete_file("path/to/delete.md", "main", "Delete file")

    # Assert
    mock_authenticate.assert_called_once()
    mock_repo.get_contents.assert_called_once_with("path/to/delete.md", ref="main")
    mock_repo.delete_file.assert_called_once_with(
        path="path/to/delete.md", message="Delete file", sha="file-sha", branch="main"
    )


@patch("src.clients.github_client.GithubClient.authenticate")
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


@patch("src.clients.github_client.GithubClient.authenticate")
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
