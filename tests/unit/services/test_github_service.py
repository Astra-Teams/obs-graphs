"""Unit tests for the GitHubService."""

from unittest.mock import MagicMock, patch

import pytest

from src.services.github_service import GitHubService


@pytest.fixture
def github_service(monkeypatch):
    """Return a GitHubService instance with mocked credentials."""
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", "/path/to/key.pem")
    monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")
    monkeypatch.setenv("GITHUB_REPO_FULL_NAME", "user/repo")
    return GitHubService()


@patch("src.services.github_service.Github")
@patch("src.services.github_service.Auth")
def test_authenticate(mock_auth, mock_github, github_service: GitHubService):
    """Test that authenticate returns a valid GitHub client."""
    # Arrange
    mock_auth.AppAuth.return_value = MagicMock()
    mock_github.return_value = MagicMock()

    # Act
    client = github_service.authenticate()

    # Assert
    assert client is not None
    mock_auth.AppAuth.assert_called_once_with("12345", "/path/to/key.pem")
    mock_github.assert_called_once()


@patch("src.services.github_service.git.Repo")
def test_clone_repository(mock_repo, github_service: GitHubService, tmp_path):
    """Test that clone_repository executes the correct git command."""
    # Arrange
    mock_repo.clone_from.return_value = MagicMock()

    # Act
    github_service.clone_repository("https://github.com/user/repo.git", tmp_path)

    # Assert
    mock_repo.clone_from.assert_called_once_with(
        "https://github.com/user/repo.git", tmp_path, branch="main"
    )


@patch("src.services.github_service.git.Repo")
def test_create_branch(mock_repo, github_service: GitHubService, tmp_path):
    """Test that create_branch creates a branch with the correct name."""
    # Arrange
    repo_instance = MagicMock()
    mock_repo.return_value = repo_instance

    # Act
    github_service.create_branch(tmp_path, "new-branch")

    # Assert
    repo_instance.git.checkout.assert_called_once_with("-b", "new-branch")


@patch("src.services.github_service.git.Repo")
def test_commit_and_push(mock_repo, github_service: GitHubService, tmp_path):
    """Test that commit_and_push stages, commits, and pushes changes."""
    # Arrange
    repo_instance = MagicMock()
    mock_repo.return_value = repo_instance

    # Act
    github_service.commit_and_push(tmp_path, "new-branch", "test commit")

    # Assert
    repo_instance.git.add.assert_called_once_with("-A")
    repo_instance.git.commit.assert_called_once_with("-m", "test commit")
    repo_instance.git.push.assert_called_once_with(
        "--set-upstream", "origin", "new-branch"
    )


@patch("src.services.github_service.Github")
def test_create_pull_request(mock_github, github_service: GitHubService):
    """Test that create_pull_request calls the GitHub API with correct parameters."""
    # Arrange
    mock_repo_obj = MagicMock()
    mock_github.get_repo.return_value = mock_repo_obj

    # Act
    github_service.create_pull_request(
        repo_full_name="user/repo",
        head_branch="new-branch",
        title="Test PR",
        body="This is a test PR.",
    )

    # Assert
    mock_github.get_repo.assert_called_once_with("user/repo")
    mock_repo_obj.create_pull.assert_called_once_with(
        title="Test PR", body="This is a test PR.", head="new-branch", base="main"
    )
