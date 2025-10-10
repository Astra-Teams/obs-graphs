"""Unit tests for GithubPRCreationAgent."""

from unittest.mock import MagicMock

import pytest

from src.obs_graphs.graphs.article_proposal.nodes.github_pr_creation import (
    GithubPRCreationAgent,
)
from src.obs_graphs.graphs.article_proposal.state import (
    AgentResult,
    FileAction,
    FileChange,
)


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client instance."""
    client = MagicMock()

    # Mock pull request object
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/test/repo/pull/1"

    client.create_pull_request.return_value = mock_pr

    return client


@pytest.fixture
def mock_vault_service():
    """Create a mock vault service instance."""
    service = MagicMock()
    service.branch = "test-branch"
    return service


@pytest.fixture
def agent(mock_github_client, mock_vault_service):
    """Create GithubPRCreationAgent instance."""
    return GithubPRCreationAgent(mock_github_client, mock_vault_service)


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


def test_validate_input_missing_node_results(agent):
    """Test that validate_input rejects missing node_results."""
    context = {
        "strategy": "new_article",
        "accumulated_changes": [],
    }
    assert agent.validate_input(context) is False


def test_execute_creates_pr_successfully(agent, mock_github_client):
    """Test successful PR creation after commit."""
    context = {
        "strategy": "new_article",
        "accumulated_changes": [
            FileChange(path="test.md", action=FileAction.CREATE, content="# Test")
        ],
        "node_results": {
            "commit_changes": {
                "success": True,
                "message": "Committed 1 changes",
                "changes_count": 0,
                "metadata": {"commit_sha": "abc123"},
            },
        },
    }

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert "Pull request created successfully" in result.message
    assert result.metadata["pr_url"] == "https://github.com/test/repo/pull/1"
    assert result.metadata["branch_name"] == "test-branch"

    mock_github_client.create_pull_request.assert_called_once()


def test_execute_no_changes_committed(agent, mock_github_client):
    """Test when no changes were committed."""
    context = {
        "strategy": "new_article",
        "accumulated_changes": [],
        "node_results": {
            "commit_changes": {
                "success": True,
                "message": "No changes to commit",
                "changes_count": 0,
                "metadata": {"commit_sha": ""},
            }
        },
    }

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert "No changes committed, skipping PR creation" in result.message
    assert result.metadata["pr_url"] == ""

    mock_github_client.create_pull_request.assert_not_called()


def test_execute_handles_pr_creation_error(agent, mock_github_client):
    """Test error handling when PR creation fails."""
    mock_github_client.create_pull_request.side_effect = Exception("PR creation failed")

    context = {
        "strategy": "new_article",
        "accumulated_changes": [
            FileChange(path="test.md", action=FileAction.CREATE, content="# Test")
        ],
        "node_results": {
            "commit_changes": {
                "success": True,
                "message": "Committed",
                "changes_count": 0,
                "metadata": {"commit_sha": "abc123"},
            }
        },
    }

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert "Failed to create pull request" in result.message


def test_execute_invalid_context_raises_error(agent):
    """Test that invalid context raises ValueError."""
    invalid_context = {"strategy": "new_article"}

    with pytest.raises(ValueError) as exc_info:
        agent.execute(invalid_context)

    assert "Invalid context" in str(exc_info.value)


def test_generate_pr_content_new_article(agent):
    """Test PR content generation for new_article strategy."""
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


def test_generate_pr_content_research_proposal(agent):
    """Test PR content generation for research_proposal strategy."""
    strategy = "research_proposal"
    node_results = {
        "article_proposal": {
            "success": True,
            "message": "Proposed research",
            "changes_count": 0,
            "metadata": {"topic_title": "AI Research", "tags": ["ai", "ml"]},
        },
        "deep_research": {
            "success": True,
            "message": "Research completed",
            "changes_count": 1,
            "metadata": {
                "proposal_filename": "ai-research.md",
                "sources_count": 5,
                "proposal_path": "proposals/ai-research.md",
            },
        },
    }
    changes = [
        FileChange(
            path="proposals/ai-research.md", action=FileAction.CREATE, content="# AI"
        )
    ]

    title, body = agent._generate_pr_content(strategy, node_results, changes)

    assert title == "Research Proposal: Ai Research"
    assert "Research Proposal" in body
    assert "Topic**: AI Research" in body
    assert "Tags**: ai, ml" in body
    assert "Sources**: 5 references" in body
    assert "proposals/ai-research.md" in body


def test_execute_with_research_proposal_strategy(agent, mock_github_client):
    """Test PR creation with research_proposal strategy."""
    context = {
        "strategy": "research_proposal",
        "accumulated_changes": [
            FileChange(
                path="proposals/quantum-computing.md",
                action=FileAction.CREATE,
                content="# Research",
            )
        ],
        "node_results": {
            "deep_research": {
                "success": True,
                "message": "Research completed",
                "changes_count": 1,
                "metadata": {"proposal_filename": "quantum-computing.md"},
            },
            "commit_changes": {
                "success": True,
                "message": "Committed",
                "changes_count": 0,
                "metadata": {"commit_sha": "def456"},
            },
        },
    }

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert "Pull request created successfully" in result.message

    # Verify PR title contains research proposal
    call_args = mock_github_client.create_pull_request.call_args
    assert "Research Proposal" in call_args[1]["title"]
