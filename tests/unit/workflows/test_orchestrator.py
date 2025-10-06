"""Unit tests for the GraphBuilder."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.api.v1.graph import (
    GraphBuilder,
    WorkflowPlan,
    WorkflowResult,
)
from src.api.v1.schemas import WorkflowRunRequest
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
    """Test that analyze_vault returns new_article strategy when no prompt is provided."""

    # Arrange - create a vault
    tmp_path.mkdir(exist_ok=True)

    graph_builder = GraphBuilder()

    # Act - test with empty prompt (empty vault)
    request_empty = WorkflowRunRequest(prompt="")
    plan_empty = graph_builder.analyze_vault(
        tmp_path, orchestrator.get_vault_service(), request_empty
    )

    # Assert
    assert isinstance(plan_empty, WorkflowPlan)
    assert plan_empty.strategy == "new_article"
    assert plan_empty.nodes == [
        "article_proposal",
        "article_content_generation",
        "github_pr_creation",
    ]

    # Act - test with vault containing many articles (10 articles)
    for i in range(10):
        (tmp_path / f"article_{i}.md").write_text("# Test Article")
    orchestrator.get_vault_service.return_value.get_vault_summary.return_value.total_articles = (
        10
    )

    request_many = WorkflowRunRequest(prompt="")
    plan_many = graph_builder.analyze_vault(
        tmp_path, orchestrator.get_vault_service(), request_many
    )

    # Assert - should still return new_article strategy
    assert isinstance(plan_many, WorkflowPlan)
    assert plan_many.strategy == "new_article"
    assert plan_many.nodes == [
        "article_proposal",
        "article_content_generation",
        "github_pr_creation",
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


def test_analyze_vault_detects_research_proposal_strategy_with_prompt(
    orchestrator, tmp_path: Path
):
    """Test that analyze_vault uses research_proposal strategy when prompt is provided."""
    # Arrange
    tmp_path.mkdir(exist_ok=True)
    graph_builder = GraphBuilder()

    request = WorkflowRunRequest(
        prompt="Research the impact of transformers on natural language processing"
    )

    # Act
    plan = graph_builder.analyze_vault(
        tmp_path, orchestrator.get_vault_service(), request
    )

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "research_proposal"
    assert plan.nodes == [
        "article_proposal",
        "deep_research",
        "github_pr_creation",
    ]


def test_analyze_vault_uses_new_article_strategy_without_prompt(
    orchestrator, tmp_path: Path
):
    """Test that analyze_vault uses new_article strategy when prompt is empty."""
    # Arrange
    tmp_path.mkdir(exist_ok=True)
    graph_builder = GraphBuilder()

    request = WorkflowRunRequest(prompt="")

    # Act
    plan = graph_builder.analyze_vault(
        tmp_path, orchestrator.get_vault_service(), request
    )

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "new_article"
    assert plan.nodes == [
        "article_proposal",
        "article_content_generation",
        "github_pr_creation",
    ]


def test_analyze_vault_uses_new_article_strategy_with_whitespace_prompt(
    orchestrator, tmp_path: Path
):
    """Test that whitespace-only prompt raises validation error."""
    # Arrange
    tmp_path.mkdir(exist_ok=True)

    # Act & Assert - whitespace-only prompt should raise validation error
    with pytest.raises(ValueError, match="Prompt cannot be whitespace-only"):
        WorkflowRunRequest(prompt="   ")


def test_execute_workflow_propagates_prompt_to_initial_state(
    orchestrator, tmp_path: Path
):
    """Test that execute_workflow includes prompt in initial state."""
    # Arrange
    tmp_path.mkdir(exist_ok=True)

    plan = WorkflowPlan(
        strategy="research_proposal",
        nodes=["article_proposal"],
    )

    graph_builder = GraphBuilder()

    # Act
    result = graph_builder.execute_workflow(
        tmp_path, plan, orchestrator, prompt="Test research prompt"
    )

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success

    # Verify node was called (indirectly via mock)
    orchestrator.get_node.assert_called()


def test_execute_workflow_with_research_proposal_strategy(orchestrator, tmp_path: Path):
    """Test that execute_workflow correctly handles research_proposal strategy."""
    # Arrange
    tmp_path.mkdir(exist_ok=True)

    plan = WorkflowPlan(
        strategy="research_proposal",
        nodes=["article_proposal", "deep_research", "github_pr_creation"],
    )

    graph_builder = GraphBuilder()

    # Act
    result = graph_builder.execute_workflow(
        tmp_path, plan, orchestrator, prompt="Research quantum computing"
    )

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 3
    assert "article_proposal" in result.node_results
    assert "deep_research" in result.node_results
    assert "github_pr_creation" in result.node_results
    assert "research_proposal" in result.summary
