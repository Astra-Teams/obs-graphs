"""Unit tests for the GraphBuilder."""

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
    def execute(self, context: dict) -> AgentResult:
        return AgentResult(
            success=True, changes=[], message=f"{self.__class__.__name__} executed"
        )


@pytest.fixture
def mock_container():
    """Return a mock DependencyContainer."""
    from src.container import DependencyContainer

    # Create a mock container
    mock_container = MagicMock(spec=DependencyContainer)
    mock_github_client = MagicMock()
    mock_vault_service = MagicMock()

    mock_container.get_github_client.return_value = mock_github_client
    mock_container.get_vault_service.return_value = mock_vault_service

    # Mock get_node to return MockAgent instances
    def mock_get_node(name):
        return MockAgent()

    mock_container.get_node.side_effect = mock_get_node

    return mock_container


def test_determine_workflow_plan_uses_new_article_strategy_without_prompt(
    mock_container,
):
    """Test that determine_workflow_plan uses new_article strategy when prompt is empty."""
    # Arrange
    graph_builder = GraphBuilder()
    request = WorkflowRunRequest(prompt="")

    # Act
    plan = graph_builder.determine_workflow_plan(
        mock_container.get_vault_service(), request
    )

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "new_article"
    assert plan.nodes == [
        "article_proposal",
        "article_content_generation",
        "commit_changes",
        "github_pr_creation",
    ]


def test_determine_workflow_plan_uses_research_proposal_strategy_with_prompt(
    mock_container,
):
    """Test that determine_workflow_plan uses research_proposal strategy when prompt is provided."""
    # Arrange
    graph_builder = GraphBuilder()
    request = WorkflowRunRequest(
        prompt="Research the impact of transformers on natural language processing"
    )

    # Act
    plan = graph_builder.determine_workflow_plan(
        mock_container.get_vault_service(), request
    )

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "research_proposal"
    assert plan.nodes == [
        "article_proposal",
        "deep_research",
        "commit_changes",
        "github_pr_creation",
    ]


def test_determine_workflow_plan_validates_whitespace_only_prompt():
    """Test that whitespace-only prompt raises validation error."""
    # Act & Assert
    with pytest.raises(ValueError, match="Prompt cannot be whitespace-only"):
        WorkflowRunRequest(prompt="   ")


def test_execute_workflow(mock_container):
    """Test that execute_workflow runs agents and aggregates results."""
    # Arrange
    plan = WorkflowPlan(
        strategy="test_plan",
        nodes=["article_proposal"],
    )

    graph_builder = GraphBuilder()

    # Act
    result = graph_builder.execute_workflow("test-branch", plan, mock_container)

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 1
    assert "article_proposal" in result.node_results


def test_execute_workflow_propagates_branch_name_to_initial_state(mock_container):
    """Test that execute_workflow includes branch_name in initial state."""
    # Arrange
    plan = WorkflowPlan(
        strategy="research_proposal",
        nodes=["article_proposal"],
    )

    graph_builder = GraphBuilder()

    # Act
    result = graph_builder.execute_workflow(
        "feature-branch", plan, mock_container, prompt="Test research prompt"
    )

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success

    # Verify node was called
    mock_container.get_node.assert_called()


def test_execute_workflow_with_research_proposal_strategy(mock_container):
    """Test that execute_workflow correctly handles research_proposal strategy."""
    # Arrange
    plan = WorkflowPlan(
        strategy="research_proposal",
        nodes=[
            "article_proposal",
            "deep_research",
            "commit_changes",
            "github_pr_creation",
        ],
    )

    graph_builder = GraphBuilder()

    # Act
    result = graph_builder.execute_workflow(
        "research-branch", plan, mock_container, prompt="Research quantum computing"
    )

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 4
    assert "article_proposal" in result.node_results
    assert "deep_research" in result.node_results
    assert "commit_changes" in result.node_results
    assert "github_pr_creation" in result.node_results
    assert "research_proposal" in result.summary


def test_execute_workflow_with_multiple_nodes(mock_container):
    """Test that execute_workflow processes multiple nodes in sequence."""
    # Arrange
    plan = WorkflowPlan(
        strategy="new_article",
        nodes=[
            "article_proposal",
            "article_content_generation",
            "commit_changes",
            "github_pr_creation",
        ],
    )

    graph_builder = GraphBuilder()

    # Act
    result = graph_builder.execute_workflow("test-branch", plan, mock_container)

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 4
    # Verify all nodes were executed
    assert mock_container.get_node.call_count == 4


@patch("src.api.v1.graph.DependencyContainer")
@patch("src.api.v1.graph.get_settings")
def test_run_workflow_creates_branch_and_executes(
    mock_get_settings, mock_container_class
):
    """Test that run_workflow creates a branch and executes the workflow."""
    # Arrange
    mock_settings = MagicMock()
    mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"
    mock_get_settings.return_value = mock_settings

    mock_container = MagicMock()
    mock_github_client = MagicMock()
    mock_vault_service = MagicMock()

    mock_container.get_github_client.return_value = mock_github_client
    mock_container.get_vault_service.return_value = mock_vault_service
    mock_container.get_node.return_value = MockAgent()

    mock_container_class.return_value = mock_container

    graph_builder = GraphBuilder()
    request = WorkflowRunRequest(prompt="Test research")

    # Act
    result = graph_builder.run_workflow(request)

    # Assert
    assert isinstance(result, WorkflowResult)
    # Verify branch was created
    mock_github_client.create_branch.assert_called_once()
    call_args = mock_github_client.create_branch.call_args
    assert call_args[1]["base_branch"] == "main"
    assert call_args[1]["branch_name"].startswith("obsidian-agents/workflow-")


@patch("src.api.v1.graph.DependencyContainer")
@patch("src.api.v1.graph.get_settings")
def test_run_workflow_handles_failure(mock_get_settings, mock_container_class):
    """Test that run_workflow handles failures gracefully."""
    # Arrange
    mock_settings = MagicMock()
    mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"
    mock_get_settings.return_value = mock_settings

    mock_container = MagicMock()
    mock_github_client = MagicMock()
    mock_github_client.create_branch.side_effect = Exception("Branch creation failed")

    mock_container.get_github_client.return_value = mock_github_client
    mock_container_class.return_value = mock_container

    graph_builder = GraphBuilder()
    request = WorkflowRunRequest(prompt="")

    # Act
    result = graph_builder.run_workflow(request)

    # Assert
    assert isinstance(result, WorkflowResult)
    assert not result.success
    assert "Branch creation failed" in result.summary
