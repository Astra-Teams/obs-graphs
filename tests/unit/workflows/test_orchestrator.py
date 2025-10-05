"""Unit tests for the GraphBuilder."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.api.v1.graph import (
    GraphBuilder,
    WorkflowPlan,
    WorkflowResult,
)
from src.state import AgentResult


class MockAgent(MagicMock):
    def execute(self, vault_path: Path, context: dict) -> AgentResult:
        return AgentResult(
            success=True, changes=[], message=f"{self.__class__.__name__} executed"
        )


@pytest.fixture
def mock_agents():
    """Fixture to mock all agent classes."""
    with (
        patch(
            "src.container.ArticleProposalAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.container.ArticleContentGenerationAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.container.FileOrganizationAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.container.CategoryOrganizationAgent",
            return_value=MockAgent(),
        ),
        patch("src.container.QualityAuditAgent", return_value=MockAgent()),
    ):
        yield


class MockVaultSummary:
    def __init__(self, total_articles=0):
        self.total_articles = total_articles
        self.categories = []
        self.recent_updates = []


@pytest.fixture
def orchestrator():
    """Return a GraphBuilder instance with mocked agents."""
    from unittest.mock import MagicMock

    from src.container import DependencyContainer

    # Create a mock container
    mock_container = MagicMock(spec=DependencyContainer)
    mock_vault_service = MagicMock()

    # Create a mock summary that can be modified
    mock_summary = MockVaultSummary()
    mock_vault_service.get_vault_summary.return_value = mock_summary

    mock_container.get_vault_service.return_value = mock_vault_service

    # Mock get_node to return MockAgent instances
    def mock_get_node(name):
        return MockAgent()

    mock_container.get_node.side_effect = mock_get_node

    return mock_container


def test_analyze_vault_always_returns_new_article_strategy(
    orchestrator,
    tmp_path: Path,
):
    """Test that analyze_vault always returns the new_article strategy regardless of vault state."""

    # Arrange - create a vault
    tmp_path.mkdir(exist_ok=True)

    graph_builder = GraphBuilder()

    # Act - test with empty vault
    plan_empty = graph_builder.analyze_vault(tmp_path, orchestrator.get_vault_service())

    # Assert
    assert isinstance(plan_empty, WorkflowPlan)
    assert plan_empty.strategy == "new_article"
    assert plan_empty.nodes == [
        "article_proposal",
        "article_content_generation",
    ]

    # Act - test with vault containing many articles (10 articles)
    for i in range(10):
        (tmp_path / f"article_{i}.md").write_text("# Test Article")
    orchestrator.get_vault_service.return_value.get_vault_summary.return_value.total_articles = (
        10
    )

    plan_many = graph_builder.analyze_vault(tmp_path, orchestrator.get_vault_service())

    # Assert - should still return new_article strategy
    assert isinstance(plan_many, WorkflowPlan)
    assert plan_many.strategy == "new_article"
    assert plan_many.nodes == [
        "article_proposal",
        "article_content_generation",
    ]


def test_execute_workflow(orchestrator, tmp_path: Path):
    """Test that execute_workflow runs agents and aggregates results."""

    # Arrange
    tmp_path.mkdir(exist_ok=True)
    # Create a simple markdown file
    (tmp_path / "test.md").write_text("# Test Article")

    # Modify the mock summary for this test
    mock_summary = (
        orchestrator.get_vault_service.return_value.get_vault_summary.return_value
    )
    mock_summary.total_articles = 5
    mock_summary.categories = ["Test"]
    mock_summary.recent_updates = ["test.md"]

    plan = WorkflowPlan(
        strategy="test_plan",
        nodes=["article_proposal"],
    )

    graph_builder = GraphBuilder()

    # Act
    result = graph_builder.execute_workflow(tmp_path, plan, orchestrator)

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 1
    assert "article_proposal" in result.node_results
