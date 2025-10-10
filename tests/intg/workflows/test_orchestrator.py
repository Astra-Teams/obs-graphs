"""Unit tests for the ArticleProposalGraph orchestration."""

from unittest.mock import MagicMock, patch

import pytest

from src.obs_graphs.api.schemas import WorkflowRunRequest
from src.obs_graphs.graphs.article_proposal.graph import (
    ArticleProposalGraph,
    WorkflowPlan,
    WorkflowResult,
)
from src.obs_graphs.graphs.article_proposal.state import AgentResult


class MockAgent(MagicMock):
    def execute(self, context: dict) -> AgentResult:
        return AgentResult(
            success=True, changes=[], message=f"{self.__class__.__name__} executed"
        )


@pytest.fixture
def mock_container():
    """Return a mock DependencyContainer."""
    from src.obs_graphs.container import DependencyContainer

    mock_container = MagicMock(spec=DependencyContainer)
    mock_vault_service = MagicMock()
    mock_container.get_vault_service.return_value = mock_vault_service

    def mock_get_node(name: str):
        return MockAgent()

    mock_container.get_node.side_effect = mock_get_node
    return mock_container


def test_determine_workflow_plan_uses_new_article_strategy_without_prompt(
    mock_container,
):
    """determine_workflow_plan should choose the new article path when no prompt is provided."""
    article_proposal_graph = ArticleProposalGraph()
    request = WorkflowRunRequest(prompt="")

    plan = article_proposal_graph.determine_workflow_plan(
        mock_container.get_vault_service(), request
    )

    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "new_article"
    assert plan.nodes == [
        "article_proposal",
        "article_content_generation",
        "submit_pull_request",
    ]


def test_determine_workflow_plan_uses_research_proposal_strategy_with_prompt(
    mock_container,
):
    """determine_workflow_plan should choose the research path when a prompt is given."""
    article_proposal_graph = ArticleProposalGraph()
    request = WorkflowRunRequest(prompt="Research transformers")

    plan = article_proposal_graph.determine_workflow_plan(
        mock_container.get_vault_service(), request
    )

    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "research_proposal"
    assert plan.nodes == [
        "article_proposal",
        "deep_research",
        "submit_pull_request",
    ]


def test_determine_workflow_plan_validates_whitespace_only_prompt():
    """A whitespace-only prompt should raise a validation error."""
    with pytest.raises(ValueError, match="Prompt cannot be whitespace-only"):
        WorkflowRunRequest(prompt="   ")


def test_execute_workflow(mock_container):
    """execute_workflow should run each node and aggregate results."""
    plan = WorkflowPlan(strategy="test_plan", nodes=["article_proposal"])
    article_proposal_graph = ArticleProposalGraph()

    result = article_proposal_graph.execute_workflow(plan, mock_container)

    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 1
    assert "article_proposal" in result.node_results


def test_execute_workflow_with_research_proposal_strategy(mock_container):
    """execute_workflow should handle the research workflow plan."""
    plan = WorkflowPlan(
        strategy="research_proposal",
        nodes=["article_proposal", "deep_research", "submit_pull_request"],
    )
    article_proposal_graph = ArticleProposalGraph()

    result = article_proposal_graph.execute_workflow(
        plan, mock_container, prompt="Research quantum computing"
    )

    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 3
    assert set(result.node_results.keys()) == {
        "article_proposal",
        "deep_research",
        "submit_pull_request",
    }
    assert "research_proposal" in result.summary


def test_execute_workflow_with_multiple_nodes(mock_container):
    """execute_workflow should process multiple nodes sequentially."""
    plan = WorkflowPlan(
        strategy="new_article",
        nodes=[
            "article_proposal",
            "article_content_generation",
            "submit_pull_request",
        ],
    )
    article_proposal_graph = ArticleProposalGraph()

    result = article_proposal_graph.execute_workflow(plan, mock_container)

    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 3
    assert mock_container.get_node.call_count == 3


@patch("src.obs_graphs.graphs.article_proposal.graph.get_container")
def test_run_workflow_collects_pr_metadata(mock_get_container):
    """run_workflow should propagate PR metadata from the submit node."""
    mock_container = MagicMock()
    mock_vault_service = MagicMock()
    mock_vault_service.get_vault_summary.return_value = MagicMock()
    mock_container.get_vault_service.return_value = mock_vault_service

    def node_factory(name: str):
        if name == "submit_pull_request":
            agent = MagicMock()

            def execute(context: dict) -> AgentResult:
                return AgentResult(
                    success=True,
                    changes=[],
                    message="Submitted",
                    metadata={
                        "branch_name": "obsidian-agents/workflow-123",
                        "pr_url": "https://github.com/test/pr/1",
                    },
                )

            agent.execute.side_effect = execute
            return agent
        return MockAgent()

    mock_container.get_node.side_effect = node_factory
    mock_get_container.return_value = mock_container

    article_proposal_graph = ArticleProposalGraph()
    request = WorkflowRunRequest(prompt="Test research")

    result = article_proposal_graph.run_workflow(request)

    assert isinstance(result, WorkflowResult)
    assert result.success
    assert result.pr_url == "https://github.com/test/pr/1"
    assert result.branch_name == "obsidian-agents/workflow-123"


@patch("src.obs_graphs.graphs.article_proposal.graph.get_container")
def test_run_workflow_handles_failure(mock_get_container):
    """run_workflow should return a failure result if a node raises."""
    mock_container = MagicMock()
    mock_vault_service = MagicMock()
    mock_vault_service.get_vault_summary.return_value = MagicMock()
    mock_container.get_vault_service.return_value = mock_vault_service

    failing_agent = MagicMock()
    failing_agent.execute.side_effect = RuntimeError("node failure")

    def node_factory(name: str):
        if name == "article_proposal":
            return failing_agent
        return MockAgent()

    mock_container.get_node.side_effect = node_factory
    mock_get_container.return_value = mock_container

    article_proposal_graph = ArticleProposalGraph()
    request = WorkflowRunRequest(prompt="")

    result = article_proposal_graph.run_workflow(request)

    assert isinstance(result, WorkflowResult)
    assert not result.success
    assert "node failure" in result.summary
