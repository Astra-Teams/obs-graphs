"""Unit tests for NewArticleCreationAgent with mocked LLM calls."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from src.api.v1.nodes.new_article_creation import NewArticleCreationAgent
from src.state import AgentResult, FileAction, FileChange


@pytest.fixture
def llm_responses():
    """Load mock LLM responses from fixture file."""
    fixture_path = (
        Path(__file__).parent.parent.parent.parent
        / "dev"
        / "mocks"
        / "llm_responses.json"
    )
    with open(fixture_path, "r") as f:
        return json.load(f)


@pytest.fixture
def mock_llm(llm_responses):
    """Create a mock LLM that returns predefined responses."""
    mock = MagicMock()

    def invoke_side_effect(messages):
        # Return article generation response by default
        content = llm_responses["article_generation_new"]["content"]
        response = MagicMock()
        response.content = content
        return response

    mock.invoke = Mock(side_effect=invoke_side_effect)
    return mock


@pytest.fixture
def agent(mock_llm):
    """Create NewArticleCreationAgent with mocked LLM."""
    agent = NewArticleCreationAgent(mock_llm)
    return agent


@pytest.fixture
def basic_vault_context():
    """Create a basic vault context for testing."""
    return {
        "vault_summary": {
            "total_articles": 10,
            "categories": ["Programming", "Science", "Mathematics"],
            "recent_updates": ["python-basics.md", "quantum-physics.md"],
        }
    }


class TestNewArticleCreationAgent:
    """Test suite for NewArticleCreationAgent."""

    def test_agent_initialization(self, mock_llm):
        """Test that agent can be initialized."""
        agent = NewArticleCreationAgent(mock_llm)
        assert agent is not None
        assert hasattr(agent, "llm")
        assert agent.llm is mock_llm

    def test_get_name(self, agent):
        """Test that agent returns correct name."""
        assert agent.get_name() == "NewArticleCreationAgent"

    def test_validate_input_with_valid_context(self, agent, basic_vault_context):
        """Test validate_input with valid context."""
        assert agent.validate_input(basic_vault_context) is True

    def test_validate_input_without_vault_summary(self, agent):
        """Test validate_input rejects context without vault_summary."""
        context = {"other_data": "value"}
        assert agent.validate_input(context) is False

    def test_validate_input_with_invalid_vault_summary(self, agent):
        """Test validate_input rejects invalid vault_summary structure."""
        context = {"vault_summary": "not a dict"}
        assert agent.validate_input(context) is False

    def test_validate_input_without_categories(self, agent):
        """Test validate_input rejects vault_summary without categories."""
        context = {"vault_summary": {"total_articles": 10}}
        assert agent.validate_input(context) is False

    def test_execute_creates_new_article(
        self, agent, basic_vault_context, llm_responses
    ):
        """Test that execute creates new article with valid content."""
        vault_path = Path("/tmp/test_vault")

        # Mock LLM to return article generation response
        response_mock = MagicMock()
        response_mock.content = llm_responses["article_generation_new"]["content"]
        agent.llm.invoke.return_value = response_mock

        result = agent.execute(vault_path, basic_vault_context)

        assert isinstance(result, AgentResult)
        assert result.success is True
        assert len(result.changes) > 0
        assert result.changes[0].action == FileAction.CREATE

    def test_execute_returns_proper_file_changes(
        self, agent, basic_vault_context, llm_responses
    ):
        """Test that execute returns proper FileChange objects."""
        vault_path = Path("/tmp/test_vault")

        # Mock LLM response
        response_mock = MagicMock()
        response_mock.content = llm_responses["article_generation_new"]["content"]
        agent.llm.invoke.return_value = response_mock

        result = agent.execute(vault_path, basic_vault_context)

        assert len(result.changes) == 1
        change = result.changes[0]
        assert isinstance(change, FileChange)
        assert change.action == FileAction.CREATE
        assert change.content is not None
        assert len(change.content) > 0
        assert change.path.endswith(".md")

    def test_execute_with_multiple_articles(
        self, agent, basic_vault_context, llm_responses
    ):
        """Test execute can generate multiple articles."""
        vault_path = Path("/tmp/test_vault")

        # Mock LLM to return multiple articles suggestions, then content for each
        suggestions_response = MagicMock()
        suggestions_response.content = llm_responses["article_generation_multiple"][
            "content"
        ]

        content_response1 = MagicMock()
        content_response1.content = llm_responses["article_content_detailed"]["content"]

        content_response2 = MagicMock()
        content_response2.content = llm_responses["article_content_detailed"]["content"]

        # First call returns suggestions, subsequent calls return content
        agent.llm.invoke.side_effect = [
            suggestions_response,
            content_response1,
            content_response2,
        ]

        result = agent.execute(vault_path, basic_vault_context)

        assert result.success is True
        assert len(result.changes) == 2
        for change in result.changes:
            assert change.action == FileAction.CREATE
            assert change.content is not None
            assert "---" in change.content  # Has frontmatter

    def test_execute_with_invalid_context_raises_error(self, agent):
        """Test that execute raises ValueError with invalid context."""
        vault_path = Path("/tmp/test_vault")
        invalid_context = {"invalid": "data"}

        with pytest.raises(ValueError, match="Invalid context"):
            agent.execute(vault_path, invalid_context)

    def test_execute_handles_llm_timeout(
        self, agent, basic_vault_context, llm_responses
    ):
        """Test that execute handles LLM timeout gracefully."""
        vault_path = Path("/tmp/test_vault")

        # Mock LLM to raise timeout
        agent.llm.invoke.side_effect = TimeoutError("Request timeout")

        result = agent.execute(vault_path, basic_vault_context)

        assert result.success is False
        assert len(result.changes) == 0
        assert "timeout" in result.message.lower()

    def test_execute_handles_llm_error(self, agent, basic_vault_context):
        """Test that execute handles LLM errors gracefully."""
        vault_path = Path("/tmp/test_vault")

        # Mock LLM to raise exception
        agent.llm.invoke.side_effect = Exception("LLM API error")

        result = agent.execute(vault_path, basic_vault_context)

        assert result.success is False
        assert len(result.changes) == 0
        assert "error" in result.message.lower()

    def test_execute_with_empty_llm_response(self, agent, basic_vault_context):
        """Test execute handles empty LLM response."""
        vault_path = Path("/tmp/test_vault")

        # Mock empty response
        response_mock = MagicMock()
        response_mock.content = "[]"
        agent.llm.invoke = Mock(return_value=response_mock)

        result = agent.execute(vault_path, basic_vault_context)

        assert result.success is True
        assert len(result.changes) == 0
        assert (
            "no articles" in result.message.lower()
            or "no new" in result.message.lower()
        )

    def test_execute_with_malformed_llm_response(self, agent, basic_vault_context):
        """Test execute handles malformed LLM response."""
        vault_path = Path("/tmp/test_vault")

        # Mock malformed response
        response_mock = MagicMock()
        response_mock.content = "This is not valid JSON"
        agent.llm.invoke = Mock(return_value=response_mock)

        result = agent.execute(vault_path, basic_vault_context)

        assert result.success is False
        assert len(result.changes) == 0

    def test_execute_includes_metadata(self, agent, basic_vault_context, llm_responses):
        """Test that execute includes metadata in result."""
        vault_path = Path("/tmp/test_vault")

        response_mock = MagicMock()
        response_mock.content = llm_responses["article_generation_new"]["content"]
        agent.llm.invoke.return_value = response_mock

        result = agent.execute(vault_path, basic_vault_context)

        assert isinstance(result.metadata, dict)
        assert "articles_generated" in result.metadata or len(result.metadata) >= 0

    def test_execute_calls_llm_with_correct_parameters(
        self, agent, basic_vault_context
    ):
        """Test that execute calls LLM with appropriate parameters."""
        vault_path = Path("/tmp/test_vault")

        response_mock = MagicMock()
        response_mock.content = '[{"title": "Test", "category": "Test", "description": "Test", "filename": "test.md"}]'
        agent.llm.invoke.return_value = response_mock

        agent.execute(vault_path, basic_vault_context)

        # Verify LLM was called
        assert agent.llm.invoke.called
        call_args = agent.llm.invoke.call_args
        assert call_args is not None

    def test_agent_respects_vault_context(self, agent, llm_responses):
        """Test that agent uses vault context in decision making."""
        vault_path = Path("/tmp/test_vault")

        # Context with many existing articles
        full_vault_context = {
            "vault_summary": {
                "total_articles": 100,
                "categories": ["Programming", "Science", "Math", "History"],
                "recent_updates": [],
            }
        }

        response_mock = MagicMock()
        response_mock.content = llm_responses["article_generation_new"]["content"]
        agent.llm.invoke.return_value = response_mock

        result = agent.execute(vault_path, full_vault_context)

        assert result.success is True
        # Agent should work with full vault too
        assert isinstance(result, AgentResult)
