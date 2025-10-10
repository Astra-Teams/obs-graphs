"""Unit tests for the prompt loader."""

import pytest

from src.obs_graphs.graphs.article_proposal.prompts.loader import render_prompt


def test_render_prompt_with_context():
    """Test rendering a prompt template with context variables."""
    # Act
    result = render_prompt(
        "new_article_creation",
        total_articles=10,
        categories=["category1", "category2"],
        recent_updates=["file1.md", "file2.md"],
    )

    # Assert
    assert "10" in result or "category1" in result or "category2" in result


def test_render_prompt_minimal_context():
    """Test rendering with minimal context."""
    # Act
    result = render_prompt("new_article_creation", total_articles=5)

    # Assert
    assert "5" in result


def test_render_prompt_unknown_template():
    """Test that unknown template raises TemplateNotFound."""
    # Act & Assert
    with pytest.raises(Exception):  # Jinja2 raises TemplateNotFound
        render_prompt("unknown_template")
