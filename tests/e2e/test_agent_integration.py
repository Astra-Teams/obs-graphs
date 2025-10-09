"""Integration tests that execute agents against real vault fixtures."""

from __future__ import annotations

from src.api.v1.schemas import WorkflowRunRequest
from src.services import VaultService
from src.state import FileAction


class TestAgentIntegration:
    """Run the orchestrator end-to-end against vault fixtures."""

    def test_new_article_agent_creates_content_in_empty_vault(
        self, vault_fixture, monkeypatch
    ) -> None:
        """An empty vault should trigger the new article agent via the orchestrator."""
        monkeypatch.setenv("USE_MOCK_LLM", "false")
        from src.container import get_container

        vault_path = vault_fixture("empty_vault")
        container = get_container()
        container.set_branch("test-branch")
        container.set_vault_path(vault_path)
        orchestrator = container.get_graph_builder()

        # Create vault service and request
        vault_service = container.get_vault_service()
        request = WorkflowRunRequest(prompt="")

        plan = orchestrator.determine_workflow_plan(vault_service, request)
        assert plan.strategy == "new_article"
        assert plan.nodes[0] == "article_proposal"

        result = orchestrator.execute_workflow(plan, container, "")
        assert result.success is True
        # The important assertion is that we got CREATE changes, not the internal prompts

        create_changes = [
            change for change in result.changes if change.action is FileAction.CREATE
        ]
        assert (
            create_changes
        ), "Expected at least one CREATE change from new article agent"

        vault_service = VaultService()
        vault_service.apply_changes(vault_path, result.changes)
        assert vault_service.validate_vault_structure(vault_path)

        created_files = [vault_path / change.path for change in create_changes]
        for created_file in created_files:
            assert created_file.exists()
            content = created_file.read_text(encoding="utf-8")
            assert "Docker Fundamentals" in content or "REST API" in content

    def test_improvement_strategy_runs_all_agents(
        self, vault_fixture, monkeypatch
    ) -> None:
        """A populated vault should trigger the improvement strategy and execute all agents."""
        monkeypatch.setenv("USE_MOCK_LLM", "false")
        from src.container import get_container

        vault_path = vault_fixture("well_maintained_vault")
        container = get_container()
        container.set_branch("test-branch")
        container.set_vault_path(vault_path)
        orchestrator = container.get_graph_builder()

        # Create vault service and request
        vault_service = container.get_vault_service()
        request = WorkflowRunRequest(prompt="test research")

        plan = orchestrator.determine_workflow_plan(vault_service, request)
        assert plan.strategy == "research_proposal"
        assert plan.nodes[0] == "article_proposal"

        result = orchestrator.execute_workflow(plan, container, "test research")
        assert result.success is True
        assert set(result.agent_results.keys()) == set(plan.agents)
        assert result.summary.startswith("Workflow completed with 'improvement'")

        # Ensure vault structure remains valid after applying no-op changes
        vault_service = VaultService()
        vault_service.apply_changes(vault_path, result.changes)
        assert vault_service.validate_vault_structure(vault_path)
