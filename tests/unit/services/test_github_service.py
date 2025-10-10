"""Tests for GithubService."""

from unittest.mock import MagicMock

from src.obs_graphs.graphs.article_proposal.state import FileAction, FileChange
from src.obs_graphs.services.github_service import GithubService


def test_commit_and_create_pr_no_changes_short_circuits():
    github_client = MagicMock()
    service = GithubService(github_client)

    pr_url = service.commit_and_create_pr(
        branch_name="test-branch",
        base_branch="main",
        changes=[],
        commit_message="Commit",
        pr_title="Title",
        pr_body="Body",
    )

    assert pr_url == ""
    github_client.create_branch.assert_not_called()
    github_client.bulk_commit_changes.assert_not_called()
    github_client.create_pull_request.assert_not_called()


def test_commit_and_create_pr_executes_in_order():
    github_client = MagicMock()
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/test/repo/pull/1"
    github_client.create_pull_request.return_value = mock_pr

    service = GithubService(github_client)

    changes = [
        FileChange(path="docs/new.md", action=FileAction.CREATE, content="# New"),
        FileChange(path="docs/old.md", action=FileAction.DELETE),
    ]

    pr_url = service.commit_and_create_pr(
        branch_name="feature-branch",
        base_branch="main",
        changes=changes,
        commit_message="Add docs",
        pr_title="Docs Update",
        pr_body="Body",
    )

    assert pr_url == "https://github.com/test/repo/pull/1"
    github_client.create_branch.assert_called_once_with(
        branch_name="feature-branch", base_branch="main"
    )
    github_client.bulk_commit_changes.assert_called_once()
    bulk_args = github_client.bulk_commit_changes.call_args.kwargs
    assert bulk_args["branch"] == "feature-branch"
    assert bulk_args["message"] == "Add docs"
    assert bulk_args["changes"][0]["content"] == "# New"
    assert bulk_args["changes"][1]["content"] is None
    github_client.create_pull_request.assert_called_once_with(
        head="feature-branch",
        base="main",
        title="Docs Update",
        body="Body",
    )
    assert pr_url == mock_pr.html_url
