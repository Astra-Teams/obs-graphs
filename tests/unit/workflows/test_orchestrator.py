from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.api.v1.graph import GraphBuilder
from src.api.v1.schemas import CreateNewArticleRequest
from src.container import DependencyContainer


def _build_container(mock_vault, mock_ollama, mock_github) -> DependencyContainer:
    container = DependencyContainer()
    container._vault_service = mock_vault
    container._ollama_client = mock_ollama
    container._github_client = mock_github
    return container


def test_run_new_article_workflow_success(tmp_path: Path):
    mock_vault = MagicMock()
    mock_vault.get_all_categories.return_value = ["Programming"]
    mock_vault.get_concatenated_content_from_category.return_value = (
        "# Title\nContent about async patterns"
    )

    mock_ollama = MagicMock()
    mock_ollama.generate.side_effect = [
        '{"keywords": ["async", "concurrency"]}',
        '{"themes": ["Async Deep Dive"]}',
    ]

    mock_pr = MagicMock(html_url="http://example.com/pr/1")
    mock_github = MagicMock()
    mock_github.create_pull_request.return_value = mock_pr

    container = _build_container(mock_vault, mock_ollama, mock_github)
    builder = GraphBuilder(container)

    request = CreateNewArticleRequest(category=None, vault_path=str(tmp_path))
    result = builder.run_new_article_workflow(request)

    assert result.success is True
    assert result.pull_request_title == "Async Deep Dive"
    assert "Async Deep Dive" in result.pull_request_body
    assert result.pr_url == "http://example.com/pr/1"
    assert result.metadata["selected_category"] == "Programming"

    mock_vault.get_all_categories.assert_called_once()
    mock_vault.get_concatenated_content_from_category.assert_called_once()
    assert mock_ollama.generate.call_count == 2
    mock_github.create_pull_request.assert_called_once()


def test_run_new_article_workflow_failure(tmp_path: Path):
    mock_vault = MagicMock()
    mock_vault.get_all_categories.side_effect = RuntimeError("vault error")

    mock_ollama = MagicMock()
    mock_github = MagicMock()

    container = _build_container(mock_vault, mock_ollama, mock_github)
    builder = GraphBuilder(container)

    request = CreateNewArticleRequest(category=None, vault_path=str(tmp_path))
    result = builder.run_new_article_workflow(request)

    assert result.success is False
    assert "vault error" in result.error
    mock_vault.get_all_categories.assert_called_once()
