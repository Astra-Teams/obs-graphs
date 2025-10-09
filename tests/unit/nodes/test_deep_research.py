"""Unit tests for DeepResearchAgent."""

from unittest.mock import MagicMock

import pytest

from src.api.v1.nodes.deep_research import DeepResearchAgent
from src.protocols.research_client_protocol import ResearchResult
from src.state import AgentResult, FileAction


@pytest.fixture
def mock_research_client():
    """Create a mock research client."""
    client = MagicMock()
    client.run_research.return_value = ResearchResult(
        summary="Comprehensive research findings on transformers in NLP.",
        sources=[
            "https://arxiv.org/abs/1706.03762",
            "https://example.com/nlp-research",
            "https://example.com/transformers-guide",
        ],
    )
    return client


@pytest.fixture
def agent(mock_research_client):
    """Create DeepResearchAgent instance."""
    return DeepResearchAgent(mock_research_client)


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "vault"
    vault.mkdir()
    # Create proposals directory
    proposals_dir = vault / "proposals"
    proposals_dir.mkdir()
    return vault


def test_validate_input_valid(agent):
    """Test that validate_input accepts valid context."""
    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }
    assert agent.validate_input(context) is True


def test_validate_input_missing_fields(agent):
    """Test that validate_input rejects missing required fields."""
    # Missing topic_title
    context = {
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }
    assert agent.validate_input(context) is False

    # Missing tags
    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "proposal_slug": "test-topic",
    }
    assert agent.validate_input(context) is False


def test_execute_with_valid_context(agent, vault_path, mock_research_client):
    """Test that execute creates proposal file successfully."""
    context = {
        "topic_title": "Impact of Transformers on NLP",
        "topic_summary": "Research on transformer architectures",
        "tags": ["transformers", "nlp", "deep-learning"],
        "proposal_slug": "impact-of-transformers-on-nlp",
    }

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert len(result.changes) == 1
    assert result.changes[0].action == FileAction.CREATE
    assert result.changes[0].path.startswith("proposals/")
    assert result.changes[0].path.endswith(".md")

    # Check metadata
    assert "proposal_filename" in result.metadata
    assert "proposal_path" in result.metadata
    assert "tags" in result.metadata
    assert "sources_count" in result.metadata
    assert result.metadata["sources_count"] == 3
    assert result.metadata["tags"] == ["transformers", "nlp", "deep-learning"]

    # Verify research client was called
    mock_research_client.run_research.assert_called_once_with(
        "Impact of Transformers on NLP"
    )


def test_execute_markdown_format(agent, vault_path, mock_research_client):
    """Test that generated Markdown has correct format."""
    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }

    result = agent.execute(context)

    assert result.success is True
    content = result.changes[0].content

    # Check YAML front matter
    assert content.startswith("---\n")
    assert "tags:\n" in content
    assert "  - tag1\n" in content
    assert "  - tag2\n" in content
    assert "  - tag3\n" in content
    assert content.count("---") == 2

    # Check Markdown sections
    assert "# Test Topic\n" in content
    assert "## Summary\n" in content
    assert "Test summary" in content
    assert "## Research Findings\n" in content
    assert "Comprehensive research findings" in content
    assert "## Sources\n" in content
    assert "1. https://arxiv.org/abs/1706.03762\n" in content


def test_execute_with_api_error(agent, vault_path, mock_research_client):
    """Test that execute handles research API errors."""
    mock_research_client.run_research.side_effect = Exception("API Error")

    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }

    result = agent.execute(context)

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert result.changes == []
    assert "error" in result.metadata
    assert "API Error" in str(result.metadata["error"])


def test_execute_with_invalid_context(agent, vault_path):
    """Test that execute raises error with invalid context."""
    context = {"topic_title": "Test"}  # Missing required fields

    with pytest.raises(ValueError, match="topic metadata"):
        agent.execute(context)


def test_execute_unique_filenames(agent, vault_path, mock_research_client):
    """Test that execute generates unique filenames with timestamps."""
    import time

    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }

    # Execute twice with delay to ensure different timestamps (format is YYYYmmdd_HHMMSS)
    result1 = agent.execute(context)
    time.sleep(1.1)  # 1.1 second delay to ensure different timestamp
    result2 = agent.execute(context)

    assert result1.success is True
    assert result2.success is True

    # Filenames should be different due to timestamps
    filename1 = result1.metadata["proposal_filename"]
    filename2 = result2.metadata["proposal_filename"]
    assert filename1 != filename2
    assert filename1.startswith("test-topic-")
    assert filename2.startswith("test-topic-")
