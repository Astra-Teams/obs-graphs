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
        from src.obs_graphs.graphs.factory import get_graph_builder
        from src.obs_graphs.services import VaultService

        vault_path = vault_fixture("empty_vault")
        vault_service = VaultService(vault_path=vault_path)

        # Get graph builder with dependencies
        graph_builder = get_graph_builder(
            workflow_type="article-proposal",
            vault_service=vault_service,
        )

        # Create request
        prompt = "Research opportunities in empty vault"
        prompts = [prompt]
        request = WorkflowRunRequest(prompts=prompts)

        result = graph_builder.run_workflow(request)
        assert result.success is True
        # The important assertion is that we got CREATE changes, not the internal prompts

        create_changes = [
            change for change in result.changes if change.action is FileAction.CREATE
        ]
        assert (
            create_changes
        ), "Expected at least one CREATE change from research workflow"

        assert vault_service.validate_vault_structure(vault_path)

    def test_improvement_strategy_runs_all_agents(self, vault_fixture) -> None:
        """A populated vault should trigger the improvement strategy and execute all agents."""
        from src.obs_graphs.graphs.factory import get_graph_builder
        from src.obs_graphs.services import VaultService

        vault_path = vault_fixture("well_maintained_vault")
        vault_service = VaultService(vault_path=vault_path)

        # Get graph builder with dependencies
        graph_builder = get_graph_builder(
            workflow_type="article-proposal",
            vault_service=vault_service,
        )

        # Create request
        prompt = "Emerging research topics"
        prompts = [prompt]
        request = WorkflowRunRequest(prompts=prompts)

        result = graph_builder.run_workflow(request)
        assert result.success is True
        assert (
            len(result.node_results) == 3
        )  # article_proposal, deep_research, submit_draft_branch
        assert result.summary.startswith("Workflow completed")

        # Ensure vault structure remains valid after applying changes
        assert vault_service.validate_vault_structure(vault_path)
