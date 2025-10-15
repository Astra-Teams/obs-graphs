"""Unit tests for the ArticleProposalGraph orchestration."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.obs_graphs.api.schemas import WorkflowRunRequest
from src.obs_graphs.graphs.article_proposal.graph import (
    ArticleProposalGraph,
    WorkflowPlan,
    WorkflowResult,
)
from src.obs_graphs.graphs.article_proposal.state import NodeResult


class MockAgent(MagicMock):
    async def execute(self, context: dict) -> NodeResult:
        return NodeResult(
            success=True, changes=[], message=f"{self.__class__.__name__} executed"
        )


@pytest.fixture
def mock_vault_service():
    """Return a mock VaultService."""
    from src.obs_graphs.graphs.article_proposal.state import VaultSummary

    mock_vault = MagicMock()
    mock_vault.get_vault_summary.return_value = VaultSummary(
        total_articles=10,
    )
    return mock_vault


@pytest.fixture
def article_proposal_graph(
    mock_vault_service,
):
    """Return an ArticleProposalGraph with mocked dependencies."""
    # Create mock nodes
    from unittest.mock import MagicMock

    mock_article_proposal_node = MagicMock()
    mock_deep_research_node = MagicMock()
    mock_submit_draft_branch_node = MagicMock()

    return ArticleProposalGraph(
        vault_service=mock_vault_service,
        article_proposal_node=mock_article_proposal_node,
        deep_research_node=mock_deep_research_node,
        submit_draft_branch_node=mock_submit_draft_branch_node,
    )


def test_determine_workflow_plan_requires_prompt(article_proposal_graph):
    """determine_workflow_plan should work with valid prompts."""
    plan = article_proposal_graph.get_default_plan(
        SimpleNamespace(prompts=["test prompt"], primary_prompt="test prompt"),
    )

    assert plan.nodes == ["article_proposal", "deep_research", "submit_draft_branch"]
    assert plan.strategy == "research_proposal"


def test_determine_workflow_plan_uses_research_proposal_strategy_with_prompt(
    article_proposal_graph,
):
    """determine_workflow_plan should choose the research path when a prompt is given."""
    request = WorkflowRunRequest(prompts=["Research transformers"])

    plan = article_proposal_graph.get_default_plan(request)

    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "research_proposal"
    assert plan.nodes == [
        "article_proposal",
        "deep_research",
        "submit_draft_branch",
    ]


def test_determine_workflow_plan_validates_whitespace_only_prompt():
    """A whitespace-only prompt should raise a validation error."""
    with pytest.raises(ValueError, match="Prompts cannot contain empty strings"):
        WorkflowRunRequest(prompts=["   "])


async def test_execute_workflow(article_proposal_graph):
    """execute_workflow should run each node and aggregate results."""
    # Mock _get_node to return mock agents instead of real nodes
    article_proposal_graph._get_node = lambda name: MockAgent()  # type: ignore[assignment]

    request = WorkflowRunRequest(prompts=["test prompt"])

    result = await article_proposal_graph.run_workflow(request)

    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 3  # All nodes should run
    assert "article_proposal" in result.node_results


async def test_execute_workflow_with_research_proposal_strategy(article_proposal_graph):
    """execute_workflow should handle the research workflow plan."""
    # Mock _get_node to return mock agents instead of real nodes
    article_proposal_graph._get_node = lambda name: MockAgent()  # type: ignore[assignment]

    request = WorkflowRunRequest(prompts=["Research quantum computing"])

    result = await article_proposal_graph.run_workflow(request)

    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 3
    assert set(result.node_results.keys()) == {
        "article_proposal",
        "deep_research",
        "submit_draft_branch",
    }
    assert "research_proposal" in result.summary


async def test_execute_workflow_with_multiple_nodes(article_proposal_graph):
    """execute_workflow should process multiple nodes sequentially."""
    # Mock _get_node to return mock agents instead of real nodes
    article_proposal_graph._get_node = lambda name: MockAgent()  # type: ignore[assignment]

    request = WorkflowRunRequest(prompts=["test research"])

    result = await article_proposal_graph.run_workflow(request)

    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.node_results) == 3


async def test_run_workflow_collects_branch_metadata(
    mock_vault_service,
):
    """run_workflow should propagate branch metadata from the submit node."""

    # Create mock nodes
    mock_article_proposal_node = MockAgent()
    mock_deep_research_node = MockAgent()
    mock_submit_draft_branch_node = MagicMock()

    async def execute(context: dict) -> NodeResult:
        return NodeResult(
            success=True,
            changes=[],
            message="Submitted",
            metadata={
                "branch_name": "obsidian-agents/workflow-123",
            },
        )

    mock_submit_draft_branch_node.execute.side_effect = execute

    # Create graph with mocked dependencies
    graph = ArticleProposalGraph(
        vault_service=mock_vault_service,
        article_proposal_node=mock_article_proposal_node,
        deep_research_node=mock_deep_research_node,
        submit_draft_branch_node=mock_submit_draft_branch_node,
    )

    request = WorkflowRunRequest(prompts=["Test research"])

    result = await graph.run_workflow(request)

    assert isinstance(result, WorkflowResult)
    assert result.success
    assert result.branch_name == "obsidian-agents/workflow-123"


async def test_run_workflow_handles_failure(
    mock_vault_service,
):
    """run_workflow should return a failure result if a node raises."""

    # Create mock nodes
    mock_article_proposal_node = MagicMock()
    mock_article_proposal_node.execute.side_effect = RuntimeError("node failure")
    mock_deep_research_node = MockAgent()
    mock_submit_draft_branch_node = MockAgent()

    # Create graph with mocked dependencies
    graph = ArticleProposalGraph(
        vault_service=mock_vault_service,
        article_proposal_node=mock_article_proposal_node,
        deep_research_node=mock_deep_research_node,
        submit_draft_branch_node=mock_submit_draft_branch_node,
    )

    request = WorkflowRunRequest(prompts=["Test research failure path"])

    result = await graph.run_workflow(request)

    assert isinstance(result, WorkflowResult)
    assert not result.success
    assert "node failure" in result.summary
