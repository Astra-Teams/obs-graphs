"""Unit tests for the prompt loader."""

import pytest

from src.api.v1.prompts.loader import render_prompt


def test_render_prompt_with_context():
    """Test rendering a prompt template with context variables."""
    # Act
    result = render_prompt(
        "article_improvement",
        article_content="# Test Article\nThis is a test.",
        vault_summary="Test vault with 10 articles",
        categories=["category1", "category2"],
    )

    # Assert
    assert "Test Article" in result
    assert "Test vault with 10 articles" in result
    assert "category1, category2" in result
    assert "# Article Improvement Prompt" in result


def test_render_prompt_minimal_context():
    """Test rendering with minimal context."""
    # Act
    result = render_prompt("quality_audit", article_content="# Test Article")

    # Assert
    assert "article_content" not in result  # Should be replaced
    assert "# Test Article" in result


def test_render_prompt_unknown_template():
    """Test that unknown template raises TemplateNotFound."""
    # Act & Assert
    with pytest.raises(Exception):  # Jinja2 raises TemplateNotFound
        render_prompt("unknown_template")
