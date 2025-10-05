"""Unit tests for ArticleImprovementAgent."""

import pytest

from src.api.v1.nodes import ArticleImprovementAgent


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
