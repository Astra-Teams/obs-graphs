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
            "src.container.NewArticleCreationAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.container.FileOrganizationAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.container.ArticleImprovementAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.container.CategoryOrganizationAgent",
            return_value=MockAgent(),
        ),
        patch("src.container.QualityAuditAgent", return_value=MockAgent()),
        patch(
            "src.container.CrossReferenceAgent",
            return_value=MockAgent(),
        ),
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


def test_analyze_vault_new_article_strategy(
    orchestrator,
    tmp_path: Path,
):
    """Test that analyze_vault determines the new_article strategy correctly."""

    # Arrange - create an empty vault (total_articles < 5)
    tmp_path.mkdir(exist_ok=True)
    orchestrator.get_vault_service.return_value.get_vault_summary.return_value.total_articles = (
        0
    )

    graph_builder = GraphBuilder()

    # Act
    plan = graph_builder.analyze_vault(tmp_path, orchestrator.get_vault_service())

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "new_article"
    assert "new_article_creation" in plan.agents


def test_analyze_vault_improvement_strategy(
    orchestrator,
    tmp_path: Path,
):
    """Test that analyze_vault determines the improvement strategy correctly."""

    # Arrange - create a vault with 10 articles (total_articles >= 5)
    tmp_path.mkdir(exist_ok=True)
    for i in range(10):
        (tmp_path / f"article_{i}.md").write_text("# Test Article")
    orchestrator.get_vault_service.return_value.get_vault_summary.return_value.total_articles = (
        10
    )

    graph_builder = GraphBuilder()

    # Act
    plan = graph_builder.analyze_vault(tmp_path, orchestrator.get_vault_service())

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "improvement"
    assert "article_improvement" in plan.agents


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
        agents=["new_article_creation", "file_organization"],
    )

    graph_builder = GraphBuilder()

    # Act
    result = graph_builder.execute_workflow(tmp_path, plan, orchestrator)

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.agent_results) == 2
    assert "new_article_creation" in result.agent_results
    assert "file_organization" in result.agent_results
