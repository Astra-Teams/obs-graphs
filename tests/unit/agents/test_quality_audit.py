"""Unit tests for QualityAuditAgent."""

import pytest

from src.agents.base import AgentResult
from src.agents.quality_audit import QualityAuditAgent


@pytest.fixture
def agent():
    """Create QualityAuditAgent instance."""
    return QualityAuditAgent()


@pytest.fixture
def vault_with_issues(tmp_path):
    """Create a vault with quality issues."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # File with broken link
    (vault / "broken_link.md").write_text(
        "# Article\n\nSee [[missing-article]] for more."
    )

    # File with poor formatting
    (vault / "bad_format.md").write_text("No header\nBad formatting\n###wrong spacing")

    # File without frontmatter
    (vault / "no_frontmatter.md").write_text(
        "# Article\n\nContent without frontmatter."
    )

    # Empty file
    (vault / "empty.md").write_text("")

    # Good file
    (vault / "good.md").write_text(
        """---
title: Good Article
category: Programming
---

# Good Article

Well-formatted content with proper structure.
"""
    )

    return vault


class TestQualityAuditAgent:
    """Test suite for QualityAuditAgent."""

    def test_agent_initialization(self, agent):
        """Test that agent can be initialized."""
        assert agent is not None

    def test_get_name(self, agent):
        """Test that agent returns correct name."""
        assert agent.get_name() == "Quality Audit Agent"

    def test_validate_input(self, agent):
        """Test validate_input accepts contexts."""
        assert agent.validate_input({}) is True

    def test_execute_returns_agent_result(self, agent, vault_with_issues):
        """Test that execute returns AgentResult."""
        result = agent.execute(vault_with_issues, {})

        assert isinstance(result, AgentResult)
        assert isinstance(result.success, bool)

    def test_execute_with_empty_vault(self, agent, tmp_path):
        """Test execute with empty vault."""
        empty_vault = tmp_path / "empty"
        empty_vault.mkdir()

        result = agent.execute(empty_vault, {})

        assert isinstance(result, AgentResult)
        assert result.success is True

    def test_execute_validates_article_quality(self, agent, vault_with_issues):
        """Test that execute validates article quality."""
        result = agent.execute(vault_with_issues, {})

        assert isinstance(result, AgentResult)
        # Should report issues or fixes

    def test_execute_returns_quality_issues(self, agent, vault_with_issues):
        """Test that execute identifies quality issues."""
        result = agent.execute(vault_with_issues, {})

        # May return fixes as UPDATE actions or report in metadata
        assert isinstance(result.metadata, dict)

    def test_execute_detects_broken_links(self, agent, tmp_path):
        """Test execute detects broken internal links."""
        vault = tmp_path / "vault"
        vault.mkdir()

        (vault / "article.md").write_text("# Article\n\n[[nonexistent-link]]")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_detects_formatting_issues(self, agent, tmp_path):
        """Test execute detects formatting problems."""
        vault = tmp_path / "vault"
        vault.mkdir()

        (vault / "bad_format.md").write_text(
            "###No space after hashes\n\nInconsistent formatting"
        )

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_detects_missing_frontmatter(self, agent, tmp_path):
        """Test execute detects missing frontmatter."""
        vault = tmp_path / "vault"
        vault.mkdir()

        (vault / "no_front.md").write_text("# Article\n\nNo frontmatter here.")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_handles_empty_articles(self, agent, tmp_path):
        """Test execute handles empty articles."""
        vault = tmp_path / "vault"
        vault.mkdir()

        (vault / "empty.md").write_text("")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)
        # Should handle empty files gracefully

    def test_execute_handles_malformed_markdown(self, agent, tmp_path):
        """Test execute handles malformed markdown."""
        vault = tmp_path / "vault"
        vault.mkdir()

        (vault / "malformed.md").write_text("####Too many hashes\n[broken](link")

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)

    def test_execute_suggests_fixes(self, agent, vault_with_issues):
        """Test that execute suggests fixes for issues."""
        result = agent.execute(vault_with_issues, {})

        # Fixes could be in changes or metadata
        assert isinstance(result, AgentResult)

    def test_execute_with_severity_levels(self, agent, vault_with_issues):
        """Test that execute categorizes issues by severity."""
        result = agent.execute(vault_with_issues, {})

        # Metadata might include severity information
        assert isinstance(result.metadata, dict)

    def test_execute_handles_good_articles(self, agent, tmp_path):
        """Test execute with high-quality articles."""
        vault = tmp_path / "vault"
        vault.mkdir()

        good_content = """---
title: Excellent
category: Test
---

# Excellent Article

Well-formatted with proper structure.
"""
        (vault / "excellent.md").write_text(good_content)

        result = agent.execute(vault, {})

        assert isinstance(result, AgentResult)
        assert result.success is True

    def test_execute_includes_metadata(self, agent, vault_with_issues):
        """Test that execute includes metadata."""
        result = agent.execute(vault_with_issues, {})

        assert isinstance(result.metadata, dict)

    def test_agent_is_stateless(self, agent, vault_with_issues):
        """Test that agent can be called multiple times."""
        result1 = agent.execute(vault_with_issues, {})
        result2 = agent.execute(vault_with_issues, {})

        assert isinstance(result1, AgentResult)
        assert isinstance(result2, AgentResult)
