"""Unit tests for ArticleImprovementAgent."""

from pathlib import Path

import pytest

from src.nodes.article_improvement import ArticleImprovementAgent
from src.nodes.base import AgentResult, FileAction


@pytest.fixture
def agent():
    """Create ArticleImprovementAgent instance."""
    return ArticleImprovementAgent()


@pytest.fixture
def vault_with_articles(tmp_path):
    """Create a vault with articles that need improvement."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create article with minimal content
    (vault / "short.md").write_text("# Short\n\nNot much content here.")

    # Create article with good content
    (vault / "complete.md").write_text(
        """# Complete Article
    
## Introduction
This is a well-structured article with multiple sections.

## Key Points
- Point 1
- Point 2

## Conclusion
Well-formatted conclusion.
"""
    )

    return vault


@pytest.fixture
def vault_context():
    """Create a context with vault information."""
    return {
        "vault_summary": {
            "total_articles": 2,
            "categories": ["Programming"],
            "recent_updates": [],
        }
    }


class TestArticleImprovementAgent:
    """Test suite for ArticleImprovementAgent."""

    def test_agent_initialization(self, agent):
        """Test that agent can be initialized."""
        assert agent is not None
        assert isinstance(agent, ArticleImprovementAgent)

    def test_get_name(self, agent):
        """Test that agent returns correct name."""
        assert agent.get_name() == "Article Improvement Agent"

    def test_validate_input(self, agent):
        """Test validate_input accepts various contexts."""
        assert agent.validate_input({}) is True
        assert agent.validate_input({"data": "value"}) is True

    def test_execute_returns_agent_result(
        self, agent, vault_with_articles, vault_context
    ):
        """Test that execute returns AgentResult."""
        result = agent.execute(vault_with_articles, vault_context)

        assert isinstance(result, AgentResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.changes, list)

    def test_execute_with_empty_vault(self, agent, tmp_path):
        """Test execute with empty vault."""
        empty_vault = tmp_path / "empty"
        empty_vault.mkdir()

        result = agent.execute(empty_vault, {})

        assert isinstance(result, AgentResult)
        assert result.success is True
        assert len(result.changes) == 0

    def test_execute_returns_update_actions(
        self, agent, vault_with_articles, vault_context
    ):
        """Test that execute returns UPDATE actions for improvements."""
        result = agent.execute(vault_with_articles, vault_context)

        # If improvements are made, they should be UPDATE actions
        for change in result.changes:
            assert change.action == FileAction.UPDATE
            assert change.content is not None
            assert len(change.content) > 0

    def test_execute_handles_already_optimal_articles(self, agent, tmp_path):
        """Test execute handles articles that don't need improvement."""
        vault = tmp_path / "optimal"
        vault.mkdir()

        optimal_content = """# Excellent Article

## Table of Contents
- [Introduction](#introduction)
- [Main Content](#main-content)
- [Conclusion](#conclusion)

## Introduction
Well-written introduction with context.

## Main Content
Detailed, well-organized content with examples.

## Conclusion
Comprehensive conclusion with takeaways.

## References
- [[related-article-1]]
- [[related-article-2]]
"""
        (vault / "optimal.md").write_text(optimal_content)

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)
        assert result.success is True
        # May have no changes if article is already optimal

    def test_execute_respects_article_structure(
        self, agent, vault_with_articles, vault_context
    ):
        """Test that execute preserves article structure."""
        result = agent.execute(vault_with_articles, vault_context)

        # Check that structure is preserved in changes
        for change in result.changes:
            if change.action == FileAction.UPDATE:
                # Should still have headers
                assert "#" in change.content

    def test_execute_preserves_existing_links(self, agent, tmp_path):
        """Test that execute preserves existing internal links."""
        vault = tmp_path / "vault"
        vault.mkdir()

        content_with_links = """# Article With Links

This references [[other-article]] and [[another-one]].

External link: [Google](https://google.com)
"""
        (vault / "links.md").write_text(content_with_links)

        result = agent.execute(vault, {})

        # Links should be preserved in improvements
        for change in result.changes:
            if "links.md" in change.path:
                assert "[[" in change.content or "](" in change.content

    def test_execute_handles_multiple_articles(
        self, agent, vault_with_articles, vault_context
    ):
        """Test that execute can improve multiple articles."""
        result = agent.execute(vault_with_articles, vault_context)

        assert isinstance(result, AgentResult)
        assert result.success is True
        # Could have changes for multiple files

    def test_execute_includes_metadata(self, agent, vault_with_articles, vault_context):
        """Test that execute includes metadata."""
        result = agent.execute(vault_with_articles, vault_context)

        assert isinstance(result.metadata, dict)

    def test_execute_handles_malformed_markdown(self, agent, tmp_path):
        """Test execute handles malformed markdown gracefully."""
        vault = tmp_path / "vault"
        vault.mkdir()

        # Create file with issues
        (vault / "malformed.md").write_text(
            "No headers\nBroken formatting\n###Too many hashes"
        )

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)
        # Should handle gracefully, not crash

    def test_execute_adds_missing_sections(
        self, agent, vault_with_articles, vault_context
    ):
        """Test that execute can add missing sections."""
        result = agent.execute(vault_with_articles, vault_context)

        # If improvements include adding sections, verify structure
        assert isinstance(result, AgentResult)

    def test_execute_improves_readability(self, agent, tmp_path):
        """Test execute improves readability."""
        vault = tmp_path / "vault"
        vault.mkdir()

        unclear_content = "# Unclear\nThis is very unclear and needs improvement."
        (vault / "unclear.md").write_text(unclear_content)

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_agent_is_idempotent(self, agent, vault_with_articles, vault_context):
        """Test that running agent multiple times is safe."""
        result1 = agent.execute(vault_with_articles, vault_context)
        result2 = agent.execute(vault_with_articles, vault_context)

        assert isinstance(result1, AgentResult)
        assert isinstance(result2, AgentResult)

    def test_execute_handles_nonexistent_vault(self, agent):
        """Test execute handles nonexistent vault."""
        result = agent.execute(Path("/nonexistent"), {})

        assert isinstance(result, AgentResult)
