"""Unit tests for ArticleProposalAgent."""

from unittest.mock import MagicMock

import pytest

from src.api.v1.nodes.article_proposal import ArticleProposalAgent
from src.state import AgentResult


@pytest.fixture
def mock_llm():
    """Create a mock LLM instance."""
    llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = """
    [
        {
            "title": "Introduction to Python",
            "category": "Programming",
            "filename": "programming/intro-python.md",
            "description": "A comprehensive guide to Python basics"
        },
        {
            "title": "Data Structures",
            "category": "Computer Science",
            "filename": "cs/data-structures.md",
            "description": "Understanding fundamental data structures"
        }
    ]
    """
    llm.invoke.return_value = mock_response
    return llm


@pytest.fixture
def agent(mock_llm):
    """Create ArticleProposalAgent instance."""
    return ArticleProposalAgent(mock_llm)


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


def test_validate_input_valid(agent):
    """Test that validate_input accepts valid context."""
    context = {"vault_summary": {"categories": ["Test"], "total_articles": 5}}
    assert agent.validate_input(context) is True


def test_validate_input_missing_vault_summary(agent):
    """Test that validate_input rejects missing vault_summary."""
    context = {}
    assert agent.validate_input(context) is False


def test_validate_input_missing_categories(agent):
    """Test that validate_input rejects missing categories."""
    context = {"vault_summary": {"total_articles": 5}}
    assert agent.validate_input(context) is False


def test_execute_with_valid_proposals(agent, vault_path):
    """Test that execute returns proposals successfully."""
    context = {
        "vault_summary": {
            "categories": ["Programming", "Computer Science"],
            "total_articles": 3,
            "recent_updates": [],
        }
    }

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.changes == []
    assert "article_proposals" in result.metadata
    assert result.metadata["proposals_count"] == 2
    assert len(result.metadata["article_proposals"]) == 2
    assert result.metadata["article_proposals"][0]["title"] == "Introduction to Python"


def test_execute_with_malformed_json(agent, vault_path, mock_llm):
    """Test that execute handles malformed JSON response."""
    mock_response = MagicMock()
    mock_response.content = "This is not valid JSON"
    mock_llm.invoke.return_value = mock_response

    context = {
        "vault_summary": {
            "categories": ["Test"],
            "total_articles": 0,
            "recent_updates": [],
        }
    }

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert "malformed_json" in result.metadata.get("error", "")


def test_execute_with_no_proposals(agent, vault_path, mock_llm):
    """Test that execute handles empty proposals list."""
    mock_response = MagicMock()
    mock_response.content = "[]"
    mock_llm.invoke.return_value = mock_response

    context = {
        "vault_summary": {
            "categories": ["Test"],
            "total_articles": 10,
            "recent_updates": [],
        }
    }

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.changes == []
    assert result.metadata["article_proposals"] == []


def test_execute_with_invalid_context(agent, vault_path):
    """Test that execute raises error with invalid context."""
    context = {}

    with pytest.raises(ValueError, match="vault_summary"):
        agent.execute(vault_path, context)
