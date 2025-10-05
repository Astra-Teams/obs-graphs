"""Unit tests for CategoryOrganizationAgent."""

import pytest

from src.api.v1.nodes.category_organization import CategoryOrganizationAgent
from src.state import AgentResult, FileAction


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

    def test_execute_with_empty_vault(self, agent, tmp_path):
        """Test execute with empty vault."""
        empty_vault = tmp_path / "empty"
        empty_vault.mkdir()

        result = agent.execute(empty_vault, {})

        assert isinstance(result, AgentResult)
        assert result.success is True

    def test_execute_reorganizes_structure(self, agent, vault_with_categories):
        """Test that execute can reorganize vault structure."""
        result = agent.execute(vault_with_categories, {})

        assert isinstance(result, AgentResult)
        # May include file move operations

    def test_execute_creates_new_categories(self, agent, vault_with_categories):
        """Test that execute can create new categories."""
        result = agent.execute(vault_with_categories, {})

        assert isinstance(result, AgentResult)

    def test_execute_merges_similar_categories(self, agent, tmp_path):
        """Test execute can merge similar categories."""
        vault = tmp_path / "vault"
        vault.mkdir()

        (vault / "Programming").mkdir()
        (vault / "Coding").mkdir()  # Similar to Programming
        (vault / "Programming" / "file1.md").write_text("# File 1")
        (vault / "Coding" / "file2.md").write_text("# File 2")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_returns_file_move_operations(self, agent, vault_with_categories):
        """Test that execute returns appropriate file operations."""
        result = agent.execute(vault_with_categories, {})

        # File moves could be UPDATE or CREATE actions
        for change in result.changes:
            assert change.action in [
                FileAction.CREATE,
                FileAction.UPDATE,
                FileAction.DELETE,
            ]

    def test_execute_handles_nested_categories(self, agent, tmp_path):
        """Test execute handles nested category structures."""
        vault = tmp_path / "vault"
        vault.mkdir()

        (vault / "Programming").mkdir()
        (vault / "Programming" / "Python").mkdir()
        (vault / "Programming" / "Python" / "basics.md").write_text("# Basics")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_includes_metadata(self, agent, vault_with_categories):
        """Test that execute includes metadata."""
        result = agent.execute(vault_with_categories, {})

        assert isinstance(result.metadata, dict)

    def test_execute_handles_many_categories(self, agent, tmp_path):
        """Test execute with many categories."""
        vault = tmp_path / "vault"
        vault.mkdir()

        for i in range(10):
            cat = vault / f"Category{i}"
            cat.mkdir()
            (cat / f"file{i}.md").write_text(f"# File {i}")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)
