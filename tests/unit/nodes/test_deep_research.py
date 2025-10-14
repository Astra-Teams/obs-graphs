"""Unit tests for DeepResearchNode."""

from unittest.mock import MagicMock

import pytest
from olm_d_rch_sdk import ResearchResponse

from src.obs_graphs.graphs.article_proposal.nodes.node2_deep_research import (
    DeepResearchNode,
)
from src.obs_graphs.graphs.article_proposal.state import FileAction, NodeResult


@pytest.fixture
def mock_research_client():
    """Create a mock research client."""
    client = MagicMock()
    client.research.return_value = ResearchResponse(
        success=True,
        article="# Impact of Transformers on NLP\n\nContent body",
        metadata={
            "sources": [
                "https://arxiv.org/abs/1706.03762",
                "https://example.com/nlp-research",
                "https://example.com/transformers-guide",
            ],
            "source_count": 3,
        },
        diagnostics=["mock"],
        processing_time=1.23,
        error_message=None,
    )
    return client


@pytest.fixture
def node(mock_research_client):
    """Create DeepResearchNode instance."""
    return DeepResearchNode(mock_research_client)


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "vault"
    vault.mkdir()
    # Create proposals directory
    proposals_dir = vault / "proposals"
    proposals_dir.mkdir()
    return vault


def test_validate_input_valid(node):
    """Test that validate_input accepts valid context."""
    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }
    assert node.validate_input(context) is True

    # Also test without tags (now optional)
    context_without_tags = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "proposal_slug": "test-topic",
    }
    assert node.validate_input(context_without_tags) is True


def test_validate_input_missing_fields(node):
    """Test that validate_input rejects missing required fields."""
    # Missing topic_title
    context = {
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }
    assert node.validate_input(context) is False

    # Empty topic_title
    context = {
        "topic_title": "",
        "topic_summary": "Test summary",
        "proposal_slug": "test-topic",
    }
    assert node.validate_input(context) is False

    # Valid context without tags (tags are now optional)
    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "proposal_slug": "test-topic",
    }
    assert node.validate_input(context) is True


@pytest.mark.asyncio
async def test_execute_with_valid_context(node, vault_path, mock_research_client):
    """Test that execute creates proposal file successfully."""
    context = {
        "topic_title": "Impact of Transformers on NLP",
        "topic_summary": "Research on transformer architectures",
        "tags": ["transformers", "nlp", "deep-learning"],
        "proposal_slug": "impact-of-transformers-on-nlp",
    }

    result = await node.execute(context)

    assert isinstance(result, NodeResult)
    assert result.success is True
    assert len(result.changes) == 1
    assert result.changes[0].action == FileAction.CREATE
    assert result.changes[0].path.startswith("proposals/")
    assert result.changes[0].path.endswith(".md")

    # Check metadata
    assert "proposal_filename" in result.metadata
    assert "proposal_path" in result.metadata
    assert "sources_count" in result.metadata
    assert result.metadata["sources_count"] == 3
    assert result.metadata["research_metadata"]["source_count"] == 3
    assert (
        result.metadata["research_metadata"]["sources"][0]
        == "https://arxiv.org/abs/1706.03762"
    )
    assert result.metadata["diagnostics"] == ["mock"]
    assert result.metadata["topic_summary"] == "Research on transformer architectures"

    # Verify research client was called
    mock_research_client.research.assert_called_once_with(
        "Impact of Transformers on NLP"
    )


@pytest.mark.asyncio
async def test_execute_preserves_article(node, vault_path, mock_research_client):
    """Test that the article returned by the client is persisted verbatim."""
    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }

    result = await node.execute(context)

    assert result.success is True
    content = result.changes[0].content

    expected_article = mock_research_client.research.return_value.article
    assert content == expected_article


@pytest.mark.asyncio
async def test_execute_with_api_error(node, vault_path, mock_research_client):
    """Test that execute handles research API errors."""
    mock_research_client.research.side_effect = Exception("API Error")

    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }

    result = await node.execute(context)

    assert isinstance(result, NodeResult)
    assert result.success is False
    assert result.changes == []
    assert "error" in result.metadata
    assert "API Error" in str(result.metadata["error"])


@pytest.mark.asyncio
async def test_execute_with_invalid_context(node, vault_path):
    """Test that execute raises error with invalid context."""
    context = {"topic_title": ""}  # Empty topic_title

    with pytest.raises(ValueError, match="topic_title is required"):
        await node.execute(context)


@pytest.mark.asyncio
async def test_execute_unique_filenames(node, vault_path, mock_research_client):
    """Test that execute generates unique filenames with timestamps."""
    import time

    context = {
        "topic_title": "Test Topic",
        "topic_summary": "Test summary",
        "tags": ["tag1", "tag2", "tag3"],
        "proposal_slug": "test-topic",
    }

    # Execute twice with delay to ensure different timestamps (format is YYYYmmdd_HHMMSS)
    result1 = await node.execute(context)
    time.sleep(1.1)  # 1.1 second delay to ensure different timestamp
    result2 = await node.execute(context)

    assert result1.success is True
    assert result2.success is True

    # Filenames should be different due to timestamps
    filename1 = result1.metadata["proposal_filename"]
    filename2 = result2.metadata["proposal_filename"]
    assert filename1 != filename2
    assert filename1.startswith("test-topic-")
    assert filename2.startswith("test-topic-")
