"""Integration tests that execute agents against real vault fixtures."""

from __future__ import annotations

from src.obs_graphs.api.schemas import WorkflowRunRequest
from src.obs_graphs.graphs.article_proposal.state import FileAction


class TestAgentIntegration:
    """Run the orchestrator end-to-end against vault fixtures."""

    def test_research_workflow_creates_proposal_in_empty_vault(
        self, vault_fixture
    ) -> None:
        """An empty vault should still run the research workflow and produce changes."""
        from src.obs_graphs.container import get_container

        vault_path = vault_fixture("empty_vault")
        container = get_container()
        container.set_branch("test-branch")
        container.set_vault_path(vault_path)
        orchestrator = container.get_graph_builder()

        # Create vault service and request
        vault_service = container.get_vault_service()
        prompt = "Research opportunities in empty vault"
        request = WorkflowRunRequest(prompt=prompt)

        plan = orchestrator.determine_workflow_plan(vault_service, request)
        assert plan.strategy == "research_proposal"
        assert plan.nodes[0] == "article_proposal"
        assert plan.nodes == [
            "article_proposal",
            "deep_research",
            "submit_pull_request",
        ]

        result = orchestrator.execute_workflow(plan, container, prompt)
        assert result.success is True
        # The important assertion is that we got CREATE changes, not the internal prompts

        create_changes = [
            change for change in result.changes if change.action is FileAction.CREATE
        ]
        assert (
            create_changes
        ), "Expected at least one CREATE change from research workflow"

        assert container.get_vault_service().validate_vault_structure(vault_path)

    def test_improvement_strategy_runs_all_agents(self, vault_fixture) -> None:
        """A populated vault should trigger the improvement strategy and execute all agents."""
        from src.obs_graphs.container import get_container

        vault_path = vault_fixture("well_maintained_vault")
        container = get_container()
        container.set_branch("test-branch")
        container.set_vault_path(vault_path)
        orchestrator = container.get_graph_builder()

        # Create vault service and request
        vault_service = container.get_vault_service()
        prompt = "Emerging research topics"
        request = WorkflowRunRequest(prompt=prompt)

        plan = orchestrator.determine_workflow_plan(vault_service, request)
        assert plan.strategy == "research_proposal"
        assert plan.nodes[0] == "article_proposal"

        result = orchestrator.execute_workflow(plan, container, prompt)
        assert result.success is True
        assert set(result.node_results.keys()) == set(plan.nodes)
        assert result.summary.startswith("Workflow completed with 'research_proposal'")

        # Ensure vault structure remains valid after applying no-op changes
        assert container.get_vault_service().validate_vault_structure(vault_path)
