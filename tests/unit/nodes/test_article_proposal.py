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
    # Return JSON format for topic proposal
    mock_response.content = """
    {
        "title": "Impact of Transformer Models on NLP",
        "summary": "This research explores how transformer architectures have revolutionized natural language processing.",
        "tags": ["transformers", "nlp", "deep-learning", "attention-mechanism"],
        "slug": "impact-of-transformer-models-on-nlp"
    }
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
    """Test that validate_input accepts valid context with prompt."""
    context = {"prompt": "Research transformers in NLP"}
    assert agent.validate_input(context) is True


def test_validate_input_missing_prompt(agent):
    """Test that validate_input rejects missing prompt."""
    context = {}
    assert agent.validate_input(context) is False


def test_validate_input_empty_prompt(agent):
    """Test that validate_input rejects empty prompt."""
    context = {"prompt": "   "}
    assert agent.validate_input(context) is False


def test_execute_with_valid_prompt(agent, vault_path):
    """Test that execute returns topic proposal successfully."""
    context = {"prompt": "Research the impact of transformers on NLP"}

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.changes == []
    assert "topic_title" in result.metadata
    assert "topic_summary" in result.metadata
    assert "tags" in result.metadata
    assert "proposal_slug" in result.metadata
    assert result.metadata["topic_title"] == "Impact of Transformer Models on NLP"
    assert len(result.metadata["tags"]) == 4
    assert result.metadata["tags"][0] == "transformers"


def test_execute_with_malformed_json(agent, vault_path, mock_llm):
    """Test that execute handles malformed JSON response."""
    mock_response = MagicMock()
    mock_response.content = "This is not valid JSON"
    mock_llm.invoke.return_value = mock_response

    context = {"prompt": "Test prompt"}

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert "malformed_json" in result.metadata.get("error", "")


def test_execute_with_invalid_tags(agent, vault_path, mock_llm):
    """Test that execute handles invalid tags in response."""
    mock_response = MagicMock()
    # Only 2 tags (less than minimum of 3)
    mock_response.content = """
    {
        "title": "Test Topic",
        "summary": "Test summary",
        "tags": ["tag1", "tag2"],
        "slug": "test-topic"
    }
    """
    mock_llm.invoke.return_value = mock_response

    context = {"prompt": "Test prompt"}

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert "malformed_json" in result.metadata.get("error", "")


def test_execute_with_invalid_context(agent, vault_path):
    """Test that execute raises error with invalid context."""
    context = {}

    with pytest.raises(ValueError, match="prompt"):
        agent.execute(vault_path, context)


def test_execute_tags_lowercase(agent, vault_path, mock_llm):
    """Test that tags are converted to lowercase."""
    mock_response = MagicMock()
    mock_response.content = """
    {
        "title": "Test Topic",
        "summary": "Test summary",
        "tags": ["Machine-Learning", "NLP", "Deep-Learning"],
        "slug": "test-topic"
    }
    """
    mock_llm.invoke.return_value = mock_response

    context = {"prompt": "Test prompt"}

    result = agent.execute(vault_path, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert all(tag.islower() or "-" in tag for tag in result.metadata["tags"])
    assert result.metadata["tags"][0] == "machine-learning"
