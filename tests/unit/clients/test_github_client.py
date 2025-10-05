"""Unit tests for the GithubClient."""

from unittest.mock import MagicMock, patch

import pytest

from src.clients.github_client import GithubClient
from src.settings import get_settings


@pytest.fixture
def github_client(monkeypatch):
    """Return a GithubClient instance with mocked credentials."""
    # Clear settings cache before setting env vars
    get_settings.cache_clear()

    monkeypatch.setenv("GITHUB_PAT", "fake-pat")
    monkeypatch.setenv("GITHUB_REPO_FULL_NAME", "user/repo")
    settings = get_settings()
    return GithubClient(settings)


@patch("src.clients.github_client.Github")
def test_authenticate(mock_github, github_client: GithubClient):
    """Test that authenticate returns a valid GitHub client."""
    # Arrange
    mock_github_instance = MagicMock()
    mock_github.return_value = mock_github_instance

    # Act
    client = github_client.authenticate()

    # Assert
    assert client is not None
    mock_github.assert_called_once_with("fake-pat")


@patch("src.clients.github_client.Repo")
@patch("src.clients.github_client.GithubClient.get_authenticated_clone_url")
def test_clone_repository(
    mock_get_url, mock_repo, github_client: GithubClient, tmp_path
):
    """Test that clone_repository executes the correct git command."""
    # Arrange
    mock_get_url.return_value = "https://x-access-token:token@github.com/user/repo.git"
    mock_repo.clone_from.return_value = MagicMock()

    # Act
    clone_path = tmp_path / "test_clone"
    github_client.clone_repository(clone_path)

    # Assert
    mock_get_url.assert_called_once_with("user/repo")
    mock_repo.clone_from.assert_called_once_with(
        "https://x-access-token:token@github.com/user/repo.git",
        clone_path,
        branch="main",
        depth=1,
    )


@patch("src.clients.github_client.Repo")
def test_create_branch(mock_repo, github_client: GithubClient, tmp_path):
    """Test that create_branch creates a branch with the correct name."""
    # Arrange
    repo_instance = MagicMock()
    # Simulate being on the default branch to skip the first checkout
    repo_instance.active_branch.name = "main"
    mock_repo.return_value = repo_instance

    # Act
    github_client.create_branch(tmp_path, "new-branch")

    # Assert
    repo_instance.git.checkout.assert_called_once_with("-b", "new-branch")


@patch("src.clients.github_client.Repo")
def test_commit_and_push(mock_repo, github_client: GithubClient, tmp_path):
    """Test that commit_and_push stages, commits, and pushes changes."""
    # Arrange
    repo_instance = MagicMock()
    repo_instance.is_dirty.return_value = True
    repo_instance.untracked_files = []
    mock_repo.return_value = repo_instance

    # Act
    result = github_client.commit_and_push(tmp_path, "new-branch", "test commit")

    # Assert
    assert result is True
    repo_instance.git.add.assert_called_once_with(A=True)
    repo_instance.index.commit.assert_called_once_with("test commit")


@patch("src.clients.github_client.Repo")
def test_commit_and_push_no_changes(mock_repo, github_client: GithubClient, tmp_path):
    """Test that commit_and_push returns False when there are no changes."""
    # Arrange
    repo_instance = MagicMock()
    repo_instance.is_dirty.return_value = False
    repo_instance.untracked_files = []
    mock_repo.return_value = repo_instance

    # Act
    result = github_client.commit_and_push(tmp_path, "new-branch", "test commit")

    # Assert
    assert result is False
    repo_instance.git.add.assert_called_once_with(A=True)


@patch("src.clients.github_client.GithubClient.authenticate")
def test_create_pull_request(mock_authenticate, github_client: GithubClient):
    """Test that create_pull_request calls the GitHub API with correct parameters."""
    # Arrange
    mock_github_client = MagicMock()
    mock_repo_obj = MagicMock()
    mock_github_client.get_repo.return_value = mock_repo_obj
    mock_authenticate.return_value = mock_github_client

    # Act
    github_client.create_pull_request(
        repo_full_name="user/repo",
        head_branch="new-branch",
        title="Test PR",
        body="This is a test PR.",
    )

    # Assert
    mock_authenticate.assert_called_once()
    mock_github_client.get_repo.assert_called_once_with("user/repo")
    mock_repo_obj.create_pull.assert_called_once_with(
        title="Test PR", body="This is a test PR.", head="new-branch", base="main"
    )
