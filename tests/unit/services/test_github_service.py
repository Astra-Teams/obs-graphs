"""Unit tests for the GitHubService."""

from unittest.mock import MagicMock, patch

import pytest

from src.config.settings import get_settings
from src.services.github_service import GitHubService


@pytest.fixture
def github_service(monkeypatch, tmp_path):
    """Return a GitHubService instance with mocked credentials."""
    # Create a temporary private key file
    key_file = tmp_path / "test_key.pem"
    key_file.write_text("fake-private-key")

    # Clear settings cache before setting env vars
    get_settings.cache_clear()

    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(key_file))
    monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")
    monkeypatch.setenv("GITHUB_REPO_FULL_NAME", "user/repo")
    monkeypatch.setenv("GITHUB_OWNER", "user")
    monkeypatch.setenv("GITHUB_REPO", "repo")
    return GitHubService()


@patch("src.services.github_service.Github")
@patch("src.services.github_service.Auth")
def test_authenticate(mock_auth, mock_github, github_service: GitHubService):
    """Test that authenticate returns a valid GitHub client."""
    # Arrange
    mock_auth.AppAuth.return_value = MagicMock()
    mock_github_instance = MagicMock()
    mock_github.return_value = mock_github_instance

    # Act
    client = github_service.authenticate()

    # Assert
    assert client is not None
    # Check that AppAuth was called (don't assert exact path as it's from tmp_path)
    mock_auth.AppAuth.assert_called_once()
    # Github is called twice: once for app auth, once for installation token
    assert mock_github.call_count == 2


@patch("src.services.github_service.Repo")
@patch("src.services.github_service.GitHubService.get_authenticated_clone_url")
def test_clone_repository(
    mock_get_url, mock_repo, github_service: GitHubService, tmp_path
):
    """Test that clone_repository executes the correct git command."""
    # Arrange
    mock_get_url.return_value = "https://x-access-token:token@github.com/user/repo.git"
    mock_repo.clone_from.return_value = MagicMock()

    # Act
    clone_path = tmp_path / "test_clone"
    github_service.clone_repository(clone_path)

    # Assert
    mock_get_url.assert_called_once_with("user/repo")
    mock_repo.clone_from.assert_called_once_with(
        "https://x-access-token:token@github.com/user/repo.git",
        clone_path,
        branch="main",
        depth=1,
    )


@patch("src.services.github_service.Repo")
def test_create_branch(mock_repo, github_service: GitHubService, tmp_path):
    """Test that create_branch creates a branch with the correct name."""
    # Arrange
    repo_instance = MagicMock()
    # Simulate being on the default branch to skip the first checkout
    repo_instance.active_branch.name = "main"
    mock_repo.return_value = repo_instance

    # Act
    github_service.create_branch(tmp_path, "new-branch")

    # Assert
    repo_instance.git.checkout.assert_called_once_with("-b", "new-branch")


@patch("src.services.github_service.Repo")
def test_commit_and_push(mock_repo, github_service: GitHubService, tmp_path):
    """Test that commit_and_push stages, commits, and pushes changes."""
    # Arrange
    repo_instance = MagicMock()
    repo_instance.is_dirty.return_value = True
    repo_instance.untracked_files = []
    mock_repo.return_value = repo_instance

    # Act
    result = github_service.commit_and_push(tmp_path, "new-branch", "test commit")

    # Assert
    assert result is True
    repo_instance.git.add.assert_called_once_with(A=True)
    repo_instance.index.commit.assert_called_once_with("test commit")


@patch("src.services.github_service.Repo")
def test_commit_and_push_no_changes(mock_repo, github_service: GitHubService, tmp_path):
    """Test that commit_and_push returns False when there are no changes."""
    # Arrange
    repo_instance = MagicMock()
    repo_instance.is_dirty.return_value = False
    repo_instance.untracked_files = []
    mock_repo.return_value = repo_instance

    # Act
    result = github_service.commit_and_push(tmp_path, "new-branch", "test commit")

    # Assert
    assert result is False
    repo_instance.git.add.assert_called_once_with(A=True)


@patch("src.services.github_service.GitHubService.authenticate")
def test_create_pull_request(mock_authenticate, github_service: GitHubService):
    """Test that create_pull_request calls the GitHub API with correct parameters."""
    # Arrange
    mock_github_client = MagicMock()
    mock_repo_obj = MagicMock()
    mock_github_client.get_repo.return_value = mock_repo_obj
    mock_authenticate.return_value = mock_github_client

    # Act
    github_service.create_pull_request(
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
