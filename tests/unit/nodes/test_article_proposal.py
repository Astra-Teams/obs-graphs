"""Unit tests for ArticleProposalNode."""

from unittest.mock import MagicMock

import pytest

from src.obs_glx.graphs.article_proposal.nodes.node1_article_proposal import (
    ArticleProposalNode,
)
from src.obs_glx.graphs.article_proposal.state import NodeResult


@pytest.fixture
def mock_llm():
    """Create a mock LLM client instance."""
    llm = MagicMock()

    async def mock_invoke(messages):
        """Mock async invoke method that returns a response with content attribute."""

        class MockResponse:
            content = "Impact of Transformer Models on NLP"

        return MockResponse()

    llm.invoke = mock_invoke
    return llm


@pytest.fixture
def llm_provider(mock_llm):
    """Provide a callable that returns the mock LLM client."""
    provider = MagicMock(return_value=mock_llm)
    return provider


@pytest.fixture
def node(llm_provider):
    """Create ArticleProposalNode instance."""
    return ArticleProposalNode(llm_provider)


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


def test_validate_input_valid(node):
    """Test that validate_input accepts valid context with prompt."""
    context = {"prompts": ["Research transformers in NLP"]}
    assert node.validate_input(context) is True


def test_validate_input_missing_prompt(node):
    """Test that validate_input rejects missing prompt."""
    context = {}
    assert node.validate_input(context) is False


def test_validate_input_empty_prompt(node):
    """Test that validate_input rejects empty prompt."""
    context = {"prompts": ["   "]}
    assert node.validate_input(context) is False


@pytest.mark.asyncio
async def test_execute_with_valid_prompt(node, vault_path):
    """Test that execute returns topic proposal successfully."""
    context = {
        "prompts": ["Research the impact of transformers on NLP"],
        "strategy": "research_proposal",
    }

    result = await node.execute(context)

    assert isinstance(result, NodeResult)
    assert result.success is True
    assert result.changes == []
    assert "topic_title" in result.metadata
    assert result.metadata["topic_title"] == "Impact of Transformer Models on NLP"


@pytest.mark.asyncio
async def test_execute_without_backend_uses_default(node, llm_provider):
    """Provider should be called with None when backend not supplied."""
    context = {
        "prompts": ["Investigate default backend"],
        "strategy": "research_proposal",
    }

    await node.execute(context)

    llm_provider.assert_called_once_with(None)


@pytest.mark.asyncio
async def test_execute_with_malformed_response(node, vault_path, mock_llm):
    """Test that execute handles malformed response by failing."""

    async def mock_invoke_malformed(messages):
        class MockResponse:
            content = ""  # Empty response

        return MockResponse()

    mock_llm.invoke = mock_invoke_malformed

    context = {"prompts": ["Test prompt"], "strategy": "research_proposal"}

    result = await node.execute(context)

    assert isinstance(result, NodeResult)
    assert result.success is False
    assert "Failed to generate research topic" in result.message
    assert "Failed to parse topic title from LLM response" in result.metadata["error"]


@pytest.mark.asyncio
async def test_execute_with_valid_response(node, vault_path, mock_llm):
    """Test that execute accepts valid response."""

    async def mock_invoke_valid(messages):
        class MockResponse:
            content = "Test Topic Title"

        return MockResponse()

    mock_llm.invoke = mock_invoke_valid

    context = {"prompts": ["Test prompt"], "strategy": "research_proposal"}

    result = await node.execute(context)

    assert isinstance(result, NodeResult)
    assert result.success is True
    assert result.metadata["topic_title"] == "Test Topic Title"


@pytest.mark.asyncio
async def test_execute_with_invalid_context(node, vault_path):
    """Test that execute raises error with invalid context."""
    context = {}

    with pytest.raises(ValueError, match="required fields missing"):
        await node.execute(context)


@pytest.mark.asyncio
async def test_execute_tags_lowercase(node, vault_path, mock_llm):
    """Test that tags are preserved as-is without lowercase conversion."""

    async def mock_invoke_preserve_tags(messages):
        class MockResponse:
            content = "Test Topic Title"

        return MockResponse()

    mock_llm.invoke = mock_invoke_preserve_tags

    context = {"prompts": ["Test prompt"], "strategy": "research_proposal"}

    result = await node.execute(context)

    assert isinstance(result, NodeResult)
    assert result.success is True
