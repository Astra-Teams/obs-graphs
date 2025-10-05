from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.api.v1.models.workflow import WorkflowStatus
from src.container import DependencyContainer
from src.db.database import get_db
from src.main import app


class _FakeSession:
    def __init__(self) -> None:
        self._id_counter = 1
        self.committed = 0
        self.instances = []

    def add(self, instance) -> None:
        self.instances.append(instance)

    def commit(self) -> None:
        self.committed += 1

    def refresh(self, instance) -> None:
        if getattr(instance, "id", None) is None:
            instance.id = self._id_counter
            self._id_counter += 1

    def close(self) -> None:
        pass


def _override_db(session: _FakeSession):
    def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db


def _reset_db_override():
    app.dependency_overrides.pop(get_db, None)


def test_successful_new_article_creation_workflow(mocker, client: TestClient):
    session = _FakeSession()
    _override_db(session)

    mock_vault = MagicMock()
    mock_vault.get_all_categories.return_value = ["Programming"]

    long_content = """# Async Basics\nAsync IO overview\n## Advanced Topics\nConcurrency patterns"""
    mock_vault.get_concatenated_content_from_category.return_value = long_content

    mock_ollama = MagicMock()

    def _generate(prompt: str) -> str:
        if "keywords" in prompt:
            return '{"keywords": ["async", "concurrency"]}'
        if "themes" in prompt:
            return '{"themes": ["Test Theme 1"]}'
        raise AssertionError("Unexpected prompt passed to Ollama")

    mock_ollama.generate.side_effect = _generate

    mock_github = MagicMock()
    mock_github.create_pull_request = mocker.spy(
        mock_github, "create_pull_request"
    )

    container = DependencyContainer()
    container._vault_service = mock_vault
    container._ollama_client = mock_ollama
    container._github_client = mock_github

    mocker.patch("src.api.v1.graph.DependencyContainer", return_value=container)

    mock_delay = mocker.patch("src.api.v1.router.run_workflow_task.delay")

    try:
        response = client.post("/api/v1/workflows/create-new-article", json={})

        assert response.status_code == 200
        payload: Dict = response.json()
        assert payload["status"] == WorkflowStatus.COMPLETED.value
        assert payload["pull_request_title"] == "Test Theme 1"
        assert "Test Theme 1についてのレポート" in payload["pull_request_body"]

        mock_vault.get_concatenated_content_from_category.assert_called_once()
        assert (
            mock_vault.get_concatenated_content_from_category.call_args.args[0]
            == "Programming"
        )
        assert isinstance(
            mock_vault.get_concatenated_content_from_category.call_args.args[1], Path
        )

        assert mock_ollama.generate.call_count == 2
        first_prompt = mock_ollama.generate.call_args_list[0].args[0]
        second_prompt = mock_ollama.generate.call_args_list[1].args[0]
        assert "\"keywords\"" in first_prompt
        assert "\"themes\"" in second_prompt

        mock_github.create_pull_request.assert_called_once()
        kwargs = mock_github.create_pull_request.call_args.kwargs
        assert kwargs["title"] == "Test Theme 1"
        assert "## Test Theme 1についてのレポート" in kwargs["body"]

        mock_delay.assert_not_called()
    finally:
        _reset_db_override()
