"""Unit tests for the GraphBuilder."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.state import AgentResult
from src.graph.builder import (
    GraphBuilder,
    WorkflowPlan,
    WorkflowResult,
)


class MockAgent(MagicMock):
    def execute(self, vault_path: Path, context: dict) -> AgentResult:
        return AgentResult(
            success=True, changes=[], message=f"{self.get_name()} executed"
        )

    def get_name(self) -> str:
        return self.__class__.__name__


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


@pytest.fixture
def orchestrator(mock_agents):
    """Return a GraphBuilder instance with mocked agents."""
    from src.container import get_container

    container = get_container()
    return container.get_graph_builder()


def test_analyze_vault_new_article_strategy(
    orchestrator: GraphBuilder,
    tmp_path: Path,
):
    """Test that analyze_vault determines the new_article strategy correctly."""
    # Arrange - create an empty vault (total_articles < 5)
    tmp_path.mkdir(exist_ok=True)

    # Act
    plan = orchestrator.analyze_vault(tmp_path)

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "new_article"
    assert "new_article_creation" in plan.agents


def test_analyze_vault_improvement_strategy(
    orchestrator: GraphBuilder,
    tmp_path: Path,
):
    """Test that analyze_vault determines the improvement strategy correctly."""
    # Arrange - create a vault with 10 articles (total_articles >= 5)
    tmp_path.mkdir(exist_ok=True)
    for i in range(10):
        (tmp_path / f"article_{i}.md").write_text("# Test Article")

    # Act
    plan = orchestrator.analyze_vault(tmp_path)

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "improvement"
    assert "article_improvement" in plan.agents


def test_execute_workflow(orchestrator: GraphBuilder, tmp_path: Path):
    """Test that execute_workflow runs agents and aggregates results."""
    # Arrange
    tmp_path.mkdir(exist_ok=True)
    # Create a simple markdown file
    (tmp_path / "test.md").write_text("# Test Article")

    plan = WorkflowPlan(
        strategy="test_plan",
        agents=["new_article_creation", "file_organization"],
    )

    # Act
    result = orchestrator.execute_workflow(tmp_path, plan)

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.agent_results) == 2
    assert "new_article_creation" in result.agent_results
    assert "file_organization" in result.agent_results
