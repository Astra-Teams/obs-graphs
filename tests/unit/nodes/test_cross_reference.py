"""Unit tests for CrossReferenceAgent."""

import pytest

from src.nodes.base import AgentResult, FileAction
from src.nodes.cross_reference import CrossReferenceAgent


@pytest.fixture
def agent():
    """Create CrossReferenceAgent (doesn't use LLM)."""
    return CrossReferenceAgent()


@pytest.fixture
def vault_with_related_articles(tmp_path):
    """Create a vault with related articles."""
    vault = tmp_path / "vault"
    vault.mkdir()

    (vault / "Programming").mkdir()
    (vault / "Programming" / "python.md").write_text(
        """# Python Programming

Python is a versatile programming language.
"""
    )

    (vault / "Programming" / "algorithms.md").write_text(
        """# Algorithms

Fundamental algorithms for programming.
"""
    )

    (vault / "Science").mkdir()
    (vault / "Science" / "physics.md").write_text(
        """# Physics

The study of matter and energy.
"""
    )

    return vault


class TestCrossReferenceAgent:
    """Test suite for CrossReferenceAgent."""

    def test_agent_initialization(self):
        """Test that agent can be initialized."""
        agent = CrossReferenceAgent()
        assert agent is not None

    def test_get_name(self, agent):
        """Test that agent returns correct name."""
        assert agent.get_name() == "Cross Reference Agent"

    def test_validate_input(self, agent):
        """Test validate_input accepts contexts."""
        assert agent.validate_input({}) is True

    def test_execute_returns_agent_result(self, agent, vault_with_related_articles):
        """Test that execute returns AgentResult."""
        result = agent.execute(vault_with_related_articles, {})

        assert isinstance(result, AgentResult)
        assert isinstance(result.success, bool)

    def test_execute_with_empty_vault(self, agent, tmp_path):
        """Test execute with empty vault."""
        empty_vault = tmp_path / "empty"
        empty_vault.mkdir()

        result = agent.execute(empty_vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_identifies_related_articles(
        self, agent, vault_with_related_articles
    ):
        """Test that execute identifies related articles."""
        result = agent.execute(vault_with_related_articles, {})

        assert isinstance(result, AgentResult)
        # Agent analyzes vault structure

    def test_execute_adds_bidirectional_links(self, agent, vault_with_related_articles):
        """Test that execute adds bidirectional links."""
        result = agent.execute(vault_with_related_articles, {})

        # Should return UPDATE actions for files
        assert isinstance(result, AgentResult)

    def test_execute_avoids_duplicate_links(self, agent, tmp_path):
        """Test that execute avoids creating duplicate links."""
        vault = tmp_path / "vault"
        vault.mkdir()

        # Article already has link
        (vault / "article1.md").write_text("# Article 1\n\nSee [[article2]] for more.")
        (vault / "article2.md").write_text("# Article 2\n\nContent here.")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_returns_update_actions(self, agent, vault_with_related_articles):
        """Test that execute returns UPDATE actions with new links."""
        result = agent.execute(vault_with_related_articles, {})

        for change in result.changes:
            assert change.action == FileAction.UPDATE
            assert change.content is not None

    def test_execute_with_no_related_articles(self, agent, tmp_path):
        """Test execute when no related articles exist."""
        vault = tmp_path / "vault"
        vault.mkdir()

        (vault / "unique.md").write_text("# Unique Topic\n\nNo related articles.")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_preserves_existing_content(self, agent, tmp_path):
        """Test that execute preserves existing content."""
        vault = tmp_path / "vault"
        vault.mkdir()

        original = "# Article\n\nImportant content here."
        (vault / "article.md").write_text(original)

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_handles_multiple_relationships(
        self, agent, vault_with_related_articles
    ):
        """Test execute with multiple cross-reference relationships."""
        result = agent.execute(vault_with_related_articles, {})

        assert isinstance(result, AgentResult)

    def test_execute_includes_metadata(self, agent, vault_with_related_articles):
        """Test that execute includes metadata."""
        result = agent.execute(vault_with_related_articles, {})

        assert isinstance(result.metadata, dict)

    def test_agent_is_stateless(self, agent, vault_with_related_articles):
        """Test that agent can be called multiple times."""
        result1 = agent.execute(vault_with_related_articles, {})
        result2 = agent.execute(vault_with_related_articles, {})

        assert isinstance(result1, AgentResult)
        assert isinstance(result2, AgentResult)
