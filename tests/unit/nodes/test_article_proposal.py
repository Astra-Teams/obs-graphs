"""Unit tests for ArticleProposalAgent."""

from unittest.mock import MagicMock

import pytest

from src.obs_graphs.graphs.article_proposal.nodes.node1_article_proposal import (
    ArticleProposalAgent,
)
from src.obs_graphs.graphs.article_proposal.state import AgentResult


@pytest.fixture
def mock_llm():
    """Create a mock LLM client instance."""
    llm = MagicMock()
    llm.invoke.return_value = """
    {
        "title": "Impact of Transformer Models on NLP",
        "summary": "This research explores how transformer architectures have revolutionized natural language processing.",
        "tags": ["transformers", "nlp", "deep-learning", "attention-mechanism"],
        "slug": "impact-of-transformer-models-on-nlp"
    }
    """
    return llm


@pytest.fixture
def llm_provider(mock_llm):
    """Provide a callable that returns the mock LLM client."""
    provider = MagicMock(return_value=mock_llm)
    return provider


@pytest.fixture
def agent(llm_provider):
    """Create ArticleProposalAgent instance."""
    return ArticleProposalAgent(llm_provider)


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


def test_validate_input_valid(agent):
    """Test that validate_input accepts valid context with prompt."""
    context = {"prompts": ["Research transformers in NLP"]}
    assert agent.validate_input(context) is True


def test_validate_input_missing_prompt(agent):
    """Test that validate_input rejects missing prompt."""
    context = {}
    assert agent.validate_input(context) is False


def test_validate_input_empty_prompt(agent):
    """Test that validate_input rejects empty prompt."""
    context = {"prompts": ["   "]}
    assert agent.validate_input(context) is False


def test_execute_with_valid_prompt(agent, vault_path):
    """Test that execute returns topic proposal successfully."""
    context = {
        "prompts": ["Research the impact of transformers on NLP"],
        "strategy": "research_proposal",
    }

    result = agent.execute(context)

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


def test_execute_passes_backend_to_provider(agent, llm_provider):
    """Ensure the backend from context is forwarded to the provider."""
    context = {
        "prompts": ["Investigate MLX performance"],
        "strategy": "research_proposal",
        "backend": "mlx",
    }

    agent.execute(context)

    llm_provider.assert_called_once_with("mlx")


def test_execute_without_backend_uses_default(agent, llm_provider):
    """Provider should be called with None when backend not supplied."""
    context = {
        "prompts": ["Investigate default backend"],
        "strategy": "research_proposal",
    }

    agent.execute(context)

    llm_provider.assert_called_once_with(None)


def test_execute_with_malformed_json(agent, vault_path, mock_llm):
    """Test that execute handles malformed JSON response."""
    mock_llm.invoke.return_value = "This is not valid JSON"

    context = {"prompts": ["Test prompt"], "strategy": "research_proposal"}

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert "malformed_json" in result.metadata.get("error", "")


def test_execute_with_invalid_tags(agent, vault_path, mock_llm):
    """Test that execute accepts any number of tags."""
    # Only 2 tags - should be accepted now
    mock_llm.invoke.return_value = """
    {
        "title": "Test Topic",
        "summary": "Test summary",
        "tags": ["tag1", "tag2"],
        "slug": "test-topic"
    }
    """

    context = {"prompts": ["Test prompt"], "strategy": "research_proposal"}

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.metadata["tags"] == ["tag1", "tag2"]


def test_execute_with_invalid_context(agent, vault_path):
    """Test that execute raises error with invalid context."""
    context = {}

    with pytest.raises(ValueError, match="required fields missing"):
        agent.execute(context)


def test_execute_tags_lowercase(agent, vault_path, mock_llm):
    """Test that tags are preserved as-is without lowercase conversion."""
    mock_llm.invoke.return_value = """
    {
        "title": "Test Topic",
        "summary": "Test summary",
        "tags": ["Machine-Learning", "NLP", "Deep-Learning"],
        "slug": "test-topic"
    }
    """

    context = {"prompts": ["Test prompt"], "strategy": "research_proposal"}

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.metadata["tags"] == ["Machine-Learning", "NLP", "Deep-Learning"]
