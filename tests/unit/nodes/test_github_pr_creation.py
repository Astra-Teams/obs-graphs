"""Unit tests for GithubPRCreationAgent."""

from unittest.mock import MagicMock

import pytest

from src.api.v1.nodes.github_pr_creation import GithubPRCreationAgent
from src.state import AgentResult, FileAction, FileChange


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client instance."""
    client = MagicMock()

    # Mock pull request object
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/test/repo/pull/1"

    client.create_branch.return_value = None
    client.commit_and_push.return_value = True
    client.create_pull_request.return_value = mock_pr

    return client


@pytest.fixture
def agent(mock_github_client):
    """Create GithubPRCreationAgent instance."""
    return GithubPRCreationAgent(mock_github_client)


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


def test_validate_input_valid(agent):
    """Test that validate_input accepts valid context."""
    context = {
        "strategy": "new_article",
        "accumulated_changes": [],
        "node_results": {},
    }
    assert agent.validate_input(context) is True


def test_validate_input_missing_strategy(agent):
    """Test that validate_input rejects missing strategy."""
    context = {
        "accumulated_changes": [],
        "node_results": {},
    }
    assert agent.validate_input(context) is False


def test_validate_input_missing_accumulated_changes(agent):
    """Test that validate_input rejects missing accumulated_changes."""
    context = {
        "strategy": "new_article",
        "node_results": {},
    }
    assert agent.validate_input(context) is False


def test_validate_input_missing_node_results(agent):
    """Test that validate_input rejects missing node_results."""
    context = {
        "strategy": "new_article",
        "accumulated_changes": [],
    }
    assert agent.validate_input(context) is False


def test_execute_creates_pr_successfully(agent, vault_path, mock_github_client):
    """Test successful PR creation."""
    context = {
        "strategy": "new_article",
        "accumulated_changes": [
            FileChange(
                path="test.md",
                action=FileAction.CREATE,
                content="# Test",
            )
        ],
        "node_results": {
            "article_proposal": {
                "success": True,
                "message": "Proposed 1 article",
                "changes_count": 0,
                "metadata": {},
            },
            "article_content_generation": {
                "success": True,
                "message": "Generated 1 article",
                "changes_count": 1,
                "metadata": {},
            },
        },
    }

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert "Pull request created successfully" in result.message
    assert result.metadata["pr_url"] == "https://github.com/test/repo/pull/1"
    assert "branch_name" in result.metadata

    # Verify GitHub client was called correctly
    mock_github_client.create_branch.assert_called_once()
    mock_github_client.commit_and_push.assert_called_once()
    mock_github_client.create_pull_request.assert_called_once()


def test_execute_no_changes_to_push(agent, vault_path, mock_github_client):
    """Test when there are no changes to push."""
    mock_github_client.commit_and_push.return_value = False

    context = {
        "strategy": "new_article",
        "accumulated_changes": [],
        "node_results": {},
    }

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.message == "No changes to commit"
    assert result.metadata["pr_url"] == ""
    assert "branch_name" in result.metadata

    # PR should not be created
    mock_github_client.create_pull_request.assert_not_called()


def test_execute_handles_github_error(agent, vault_path, mock_github_client):
    """Test error handling when GitHub operations fail."""
    mock_github_client.create_branch.side_effect = Exception("GitHub API error")

    context = {
        "strategy": "new_article",
        "accumulated_changes": [
            FileChange(path="test.md", action=FileAction.CREATE, content="# Test")
        ],
        "node_results": {},
    }

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert "Failed to create pull request" in result.message
    assert "error" in result.metadata


def test_execute_invalid_context_raises_error(agent, vault_path):
    """Test that invalid context raises ValueError."""
    invalid_context = {"strategy": "new_article"}  # Missing required keys

    with pytest.raises(ValueError) as exc_info:
        agent.execute(vault_path, invalid_context)

    assert "Invalid context" in str(exc_info.value)


def test_generate_commit_message(agent):
    """Test commit message generation."""
    strategy = "new_article"
    node_results = {
        "article_proposal": {
            "success": True,
            "message": "Proposed 2 articles",
            "changes_count": 0,
            "metadata": {},
        },
        "article_content_generation": {
            "success": True,
            "message": "Generated 2 articles",
            "changes_count": 2,
            "metadata": {},
        },
    }
    changes = [
        FileChange(path="test1.md", action=FileAction.CREATE, content="# Test 1"),
        FileChange(path="test2.md", action=FileAction.CREATE, content="# Test 2"),
    ]

    message = agent._generate_commit_message(strategy, node_results, changes)

    assert "new_article" in message
    assert "article_proposal: Proposed 2 articles" in message
    assert "article_content_generation: Generated 2 articles" in message
    assert "Obsidian Agents workflow" in message


def test_generate_pr_content(agent):
    """Test PR content generation."""
    strategy = "new_article"
    node_results = {
        "article_proposal": {
            "success": True,
            "message": "Proposed 1 article",
            "changes_count": 0,
            "metadata": {},
        },
    }
    changes = [FileChange(path="test.md", action=FileAction.CREATE, content="# Test")]

    title, body = agent._generate_pr_content(strategy, node_results, changes)

    assert title == "Automated vault improvements (new_article)"
    assert "new_article" in body
    assert "1 file operations" in body
    assert "article_proposal" in body
    assert "✅ Success" in body
    assert "Obsidian Nodes Workflow Automation" in body
