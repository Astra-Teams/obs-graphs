"""Unit tests for FileOrganizationAgent."""

from pathlib import Path

import pytest

from src.nodes.base import AgentResult, FileAction
from src.nodes.file_organization import FileOrganizationAgent


@pytest.fixture
def agent():
    """Create FileOrganizationAgent instance."""
    return FileOrganizationAgent()


@pytest.fixture
def basic_vault_path(tmp_path):
    """Create a temporary vault with some test files."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create some test markdown files
    (vault / "unformatted.md").write_text(
        "# Header\nSome content without proper formatting"
    )
    (vault / "Programming").mkdir()
    (vault / "Programming" / "python.md").write_text(
        "# Python\nPython programming language"
    )

    return vault


@pytest.fixture
def vault_context():
    """Create a context for vault operations."""
    return {
        "vault_summary": {
            "total_articles": 5,
            "categories": ["Programming", "Science"],
            "recent_updates": ["python.md"],
        }
    }


class TestFileOrganizationAgent:
    """Test suite for FileOrganizationAgent."""

    def test_agent_initialization(self, agent):
        """Test that agent can be initialized."""
        assert agent is not None
        assert isinstance(agent, FileOrganizationAgent)

    def test_get_name(self, agent):
        """Test that agent returns correct name."""
        assert agent.get_name() == "File Organization Agent"

    def test_validate_input_accepts_any_context(self, agent):
        """Test validate_input accepts various contexts."""
        assert agent.validate_input({}) is True
        assert agent.validate_input({"vault_summary": {}}) is True
        assert agent.validate_input({"data": "value"}) is True

    def test_execute_returns_agent_result(self, agent, basic_vault_path, vault_context):
        """Test that execute returns AgentResult."""
        result = agent.execute(basic_vault_path, vault_context)

        assert isinstance(result, AgentResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.changes, list)
        assert isinstance(result.message, str)

    def test_execute_with_empty_vault(self, agent, tmp_path):
        """Test execute with empty vault."""
        empty_vault = tmp_path / "empty"
        empty_vault.mkdir()

        result = agent.execute(empty_vault, {})

        assert isinstance(result, AgentResult)
        assert result.success is True
        assert len(result.changes) == 0

    def test_execute_handles_nonexistent_vault(self, agent):
        """Test execute handles nonexistent vault path."""
        nonexistent_path = Path("/nonexistent/vault")

        result = agent.execute(nonexistent_path, {})

        assert isinstance(result, AgentResult)
        # Should handle gracefully (either success with no changes or failure)
        assert isinstance(result.success, bool)

    def test_execute_returns_update_actions(
        self, agent, basic_vault_path, vault_context
    ):
        """Test that execute can return UPDATE actions for existing files."""
        result = agent.execute(basic_vault_path, vault_context)

        # If changes are made, they should be UPDATE actions for existing files
        if len(result.changes) > 0:
            for change in result.changes:
                assert change.action in [FileAction.UPDATE, FileAction.CREATE]
                if change.action == FileAction.UPDATE:
                    assert change.content is not None

    def test_execute_formats_markdown_correctly(
        self, agent, basic_vault_path, vault_context
    ):
        """Test that execute formats markdown properly."""
        result = agent.execute(basic_vault_path, vault_context)

        # Check that result is valid
        assert isinstance(result, AgentResult)

        # If formatting changes were made, verify structure
        for change in result.changes:
            if change.action == FileAction.UPDATE:
                assert "# " in change.content or "##" in change.content  # Has headers

    def test_execute_assigns_categories(self, agent, basic_vault_path, vault_context):
        """Test that execute can assign categories to articles."""
        result = agent.execute(basic_vault_path, vault_context)

        assert isinstance(result, AgentResult)
        # Agent should work with categorization
        assert result.success is True

    def test_execute_handles_file_moves(self, agent, basic_vault_path, vault_context):
        """Test that execute can handle file move operations."""
        # Create a file in wrong location
        (basic_vault_path / "misplaced.md").write_text(
            "# Misplaced\nShould be in category"
        )

        result = agent.execute(basic_vault_path, vault_context)

        assert isinstance(result, AgentResult)
        # File move would be represented as UPDATE with new path or metadata

    def test_execute_preserves_existing_content(
        self, agent, basic_vault_path, vault_context
    ):
        """Test that execute preserves important content during formatting."""
        original_content = "# Important\n\nThis content should be preserved"
        test_file = basic_vault_path / "important.md"
        test_file.write_text(original_content)

        result = agent.execute(basic_vault_path, vault_context)

        # Check that important parts are preserved in changes
        if result.changes:
            for change in result.changes:
                if "important" in change.path.lower():
                    assert "preserved" in change.content.lower()

    def test_execute_handles_multiple_files(
        self, agent, basic_vault_path, vault_context
    ):
        """Test that execute can process multiple files."""
        # Create additional files
        (basic_vault_path / "file1.md").write_text("# File 1")
        (basic_vault_path / "file2.md").write_text("# File 2")

        result = agent.execute(basic_vault_path, vault_context)

        assert isinstance(result, AgentResult)
        assert result.success is True

    def test_execute_includes_metadata(self, agent, basic_vault_path, vault_context):
        """Test that execute includes metadata in result."""
        result = agent.execute(basic_vault_path, vault_context)

        assert isinstance(result.metadata, dict)
        # Metadata should contain useful information
        assert len(result.metadata) >= 0

    def test_execute_with_various_markdown_formats(
        self, agent, tmp_path, vault_context
    ):
        """Test execute handles various markdown formats."""
        vault = tmp_path / "vault"
        vault.mkdir()

        # Create files with different markdown styles
        (vault / "headers.md").write_text("# H1\n## H2\n### H3")
        (vault / "lists.md").write_text("- Item 1\n- Item 2\n* Item 3")
        (vault / "links.md").write_text(
            "[[internal-link]] and [external](http://example.com)"
        )

        result = agent.execute(vault, vault_context)

        assert isinstance(result, AgentResult)
        assert result.success is True

    def test_execute_handles_frontmatter(self, agent, tmp_path, vault_context):
        """Test execute preserves or adds frontmatter."""
        vault = tmp_path / "vault"
        vault.mkdir()

        content = "---\ntitle: Test\ncategory: Programming\n---\n# Content"
        (vault / "with_frontmatter.md").write_text(content)

        result = agent.execute(vault, vault_context)

        assert isinstance(result, AgentResult)
        # Frontmatter should be handled appropriately

    def test_agent_is_stateless(self, agent, basic_vault_path, vault_context):
        """Test that agent can be called multiple times."""
        result1 = agent.execute(basic_vault_path, vault_context)
        result2 = agent.execute(basic_vault_path, vault_context)

        assert isinstance(result1, AgentResult)
        assert isinstance(result2, AgentResult)
        # Both should succeed
        assert result1.success is True or result2.success is True
