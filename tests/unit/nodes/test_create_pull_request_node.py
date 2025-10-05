from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.api.v1.nodes.create_pull_request import CreatePullRequestNode


@pytest.fixture
def settings_stub(monkeypatch: pytest.MonkeyPatch):
    settings = MagicMock()
    settings.OBSIDIAN_VAULT_REPO_FULL_NAME = "owner/repo"
    settings.WORKFLOW_DEFAULT_BRANCH = "main"

    def _get_settings():
        return settings

    monkeypatch.setattr(
        "src.api.v1.nodes.create_pull_request.get_settings", _get_settings
    )
    return settings


def test_create_pull_request_calls_github(settings_stub):
    container = MagicMock()
    github_client = MagicMock()
    container.get_github_client.return_value = github_client
    node = CreatePullRequestNode(container)

    github_client.create_pull_request.return_value = MagicMock(html_url="http://pr")

    result = node.execute(
        Path("/tmp"),
        {
            "selected_theme": "Test Theme 1",
            "report_markdown": "## Test Theme 1についてのレポート",
            "selected_category": "Programming",
            "keywords": ["async"],
        },
    )

    github_client.create_pull_request.assert_called_once()
    kwargs = github_client.create_pull_request.call_args.kwargs
    assert kwargs["title"] == "Test Theme 1"
    assert "Test Theme 1についてのレポート" in kwargs["body"]
    assert result.metadata["state_updates"]["pull_request"]["url"] == "http://pr"


def test_create_pull_request_requires_fields(settings_stub):
    container = MagicMock()
    node = CreatePullRequestNode(container)

    with pytest.raises(ValueError):
        node.execute(Path("/tmp"), {"report_markdown": "content"})
