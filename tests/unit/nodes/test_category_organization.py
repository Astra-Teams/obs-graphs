"""Unit tests for CategoryOrganizationAgent."""

import pytest

from src.api.v1.nodes import CategoryOrganizationAgent


@pytest.fixture
def agent():
    """Create CategoryOrganizationAgent instance."""
    return CategoryOrganizationAgent()


@pytest.fixture
def vault_with_categories(tmp_path):
    """Create a vault with category structure."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create categories
    (vault / "Programming").mkdir()
    (vault / "Science").mkdir()
    (vault / "Programming" / "python.md").write_text("# Python")
    (vault / "Science" / "physics.md").write_text("# Physics")

    # Uncategorized file
    (vault / "uncategorized.md").write_text("# Needs Category")

    return vault


class TestCategoryOrganizationAgent:
    """Test suite for CategoryOrganizationAgent."""

    def test_execute_includes_metadata(self, agent, vault_with_categories):
        """Test that execute includes metadata."""
        result = agent.execute(vault_with_categories, {})

        assert isinstance(result.metadata, dict)
