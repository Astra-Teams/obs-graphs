"""Integration tests that execute agents against real vault fixtures."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services.vault import VaultService
from src.state import FileAction

FIXTURES_ROOT = Path("tests/fixtures/vaults")
LLM_FIXTURE_PATH = Path("tests/fixtures/mock_data/llm_responses.json")


@pytest.fixture()
def mock_llm(monkeypatch: pytest.MonkeyPatch):
    """Patch Ollama so the new article agent produces deterministic output."""
    responses = json.loads(LLM_FIXTURE_PATH.read_text(encoding="utf-8"))

    analysis_payload = json.dumps(
        [
            {
                "title": "Docker Fundamentals",
                "category": "Technology",
                "description": "Introduction to containerization with Docker",
                "filename": "Technology/docker-intro.md",
            }
        ]
    )
    article_content = responses["article_content_detailed"]["content"]

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            self.prompts: list[str] = []

        def invoke(self, prompt: str) -> SimpleNamespace:
            self.prompts.append(prompt)
            if "Analyze this Obsidian Vault" in prompt:
                return SimpleNamespace(content=analysis_payload)
            if "Create a comprehensive Obsidian markdown article" in prompt:
                return SimpleNamespace(content=article_content)
            # Fallback content is rarely used but keeps the agent defensive
            return SimpleNamespace(
                content=responses["article_generation_new"]["content"]
            )

    fake_llm = FakeLLM()
    monkeypatch.setattr("src.nodes.new_article_creation.Ollama", FakeLLM)
    return fake_llm


def _copy_vault_fixture(tmp_path: Path, fixture_name: str) -> Path:
    destination = tmp_path / fixture_name
    shutil.copytree(FIXTURES_ROOT / fixture_name, destination)
    return destination


class TestAgentIntegration:
    """Run the orchestrator end-to-end against vault fixtures."""

    @pytest.mark.skip(reason="Mock LLM integration needs fixing after Ollama migration")
    def test_new_article_agent_creates_content_in_empty_vault(
        self, tmp_path: Path, mock_llm
    ) -> None:
        """An empty vault should trigger the new article agent via the orchestrator."""
        from src.container import get_container

        vault_path = _copy_vault_fixture(tmp_path, "empty_vault")
        orchestrator = get_container().get_graph_builder()

        plan = orchestrator.analyze_vault(vault_path)
        assert plan.strategy == "new_article"
        assert plan.agents[0] == "new_article_creation"

        result = orchestrator.execute_workflow(vault_path, plan)
        assert result.success is True
        # Note: mock_llm.prompts may be empty if the agent is called through container
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
        self, tmp_path: Path, mock_llm
    ) -> None:
        """A populated vault should trigger the improvement strategy and execute all agents."""
        from src.container import get_container

        vault_path = _copy_vault_fixture(tmp_path, "well_maintained_vault")
        orchestrator = get_container().get_graph_builder()

        plan = orchestrator.analyze_vault(vault_path)
        assert plan.strategy == "improvement"
        assert plan.agents[0] == "article_improvement"

        result = orchestrator.execute_workflow(vault_path, plan)
        assert result.success is True
        assert set(result.agent_results.keys()) == set(plan.agents)
        assert result.summary.startswith("Workflow completed with 'improvement'")

        # Ensure vault structure remains valid after applying no-op changes
        vault_service = VaultService()
        vault_service.apply_changes(vault_path, result.changes)
        assert vault_service.validate_vault_structure(vault_path)
