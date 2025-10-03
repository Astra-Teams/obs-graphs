"""Unit tests for the WorkflowOrchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.base import AgentResult
from src.services.vault_service import VaultSummary
from src.workflows.orchestrator import (
    WorkflowOrchestrator,
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
            "src.workflows.orchestrator.NewArticleCreationAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.workflows.orchestrator.FileOrganizationAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.workflows.orchestrator.ArticleImprovementAgent",
            return_value=MockAgent(),
        ),
        patch(
            "src.workflows.orchestrator.CategoryOrganizationAgent",
            return_value=MockAgent(),
        ),
        patch("src.workflows.orchestrator.QualityAuditAgent", return_value=MockAgent()),
        patch(
            "src.workflows.orchestrator.CrossReferenceAgent",
            return_value=MockAgent(),
        ),
    ):
        yield


@pytest.fixture
def orchestrator(mock_agents):
    """Return a WorkflowOrchestrator instance with mocked agents."""
    return WorkflowOrchestrator()


@patch("src.workflows.orchestrator.VaultService")
def test_analyze_vault_new_article_strategy(
    mock_vault_service,
    orchestrator: WorkflowOrchestrator,
    tmp_path: Path,
):
    """Test that analyze_vault determines the new_article strategy correctly."""
    # Arrange
    mock_vault_service.get_vault_summary.return_value = VaultSummary(
        total_articles=0, categories=[], recent_updates=[]
    )

    # Act
    plan = orchestrator.analyze_vault(tmp_path)

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "new_article"
    assert "NewArticleCreationAgent" in [
        agent.__class__.__name__ for agent in plan.agents
    ]


@patch("src.workflows.orchestrator.VaultService")
def test_analyze_vault_improvement_strategy(
    mock_vault_service,
    orchestrator: WorkflowOrchestrator,
    tmp_path: Path,
):
    """Test that analyze_vault determines the improvement strategy correctly."""
    # Arrange
    mock_vault_service.get_vault_summary.return_value = VaultSummary(
        total_articles=10, categories=["Test"], recent_updates=["test.md"]
    )

    # Act
    plan = orchestrator.analyze_vault(tmp_path)

    # Assert
    assert isinstance(plan, WorkflowPlan)
    assert plan.strategy == "improvement"
    assert "ArticleImprovementAgent" in [
        agent.__class__.__name__ for agent in plan.agents
    ]


def test_execute_workflow(orchestrator: WorkflowOrchestrator, tmp_path: Path):
    """Test that execute_workflow runs agents and aggregates results."""
    # Arrange
    plan = WorkflowPlan(
        strategy="test_plan",
        agents=[
            MagicMock(spec=MockAgent)(),
            MagicMock(spec=MockAgent)(),
        ],
    )

    # Act
    result = orchestrator.execute_workflow(tmp_path, plan)

    # Assert
    assert isinstance(result, WorkflowResult)
    assert result.success
    assert len(result.agent_results) == 2
