"""Unit tests for SubmitPullRequestAgent."""

from unittest.mock import MagicMock

import pytest

from src.obs_graphs.graphs.article_proposal.nodes.node3_submit_pull_request import (
    SubmitPullRequestAgent,
)
from src.obs_graphs.graphs.article_proposal.state import FileAction, FileChange


@pytest.fixture
def github_service():
    service = MagicMock()
    service.commit_and_create_pr.return_value = "https://github.com/test/repo/pull/1"
    return service


@pytest.fixture
def agent(github_service):
    return SubmitPullRequestAgent(github_service)


def test_validate_input_valid(agent):
    context = {
        "strategy": "new_article",
        "accumulated_changes": [],
        "node_results": {},
    }
    assert agent.validate_input(context) is True


def test_validate_input_missing_keys(agent):
    context = {"strategy": "new_article"}
    assert agent.validate_input(context) is False


def test_execute_with_no_changes_skips_github(agent, github_service):
    context = {
        "strategy": "new_article",
        "accumulated_changes": [],
        "node_results": {},
    }

    result = agent.execute(context)

    assert result.success is True
    assert result.metadata == {"branch_name": "", "pr_url": ""}
    github_service.commit_and_create_pr.assert_not_called()


def test_execute_calls_github_service(agent, github_service, monkeypatch):
    changes = [
        FileChange(path="test.md", action=FileAction.CREATE, content="# Test"),
    ]
    context = {
        "strategy": "new_article",
        "accumulated_changes": changes,
        "node_results": {"article_proposal": {"success": True, "message": "done"}},
    }

    monkeypatch.setattr(agent, "_generate_branch_name", lambda: "test-branch")
    monkeypatch.setattr(agent, "_generate_commit_message", lambda *args: "Commit")
    monkeypatch.setattr(
        agent, "_generate_pr_content", lambda *args: ("PR Title", "PR Body")
    )

    result = agent.execute(context)

    github_service.commit_and_create_pr.assert_called_once_with(
        branch_name="test-branch",
        base_branch="main",
        changes=changes,
        commit_message="Commit",
        pr_title="PR Title",
        pr_body="PR Body",
    )

    assert result.success is True
    assert result.metadata["branch_name"] == "test-branch"
    assert result.metadata["pr_url"] == "https://github.com/test/repo/pull/1"


def test_execute_handles_exception(agent, github_service, monkeypatch):
    changes = [
        FileChange(path="test.md", action=FileAction.CREATE, content="# Test"),
    ]
    context = {
        "strategy": "new_article",
        "accumulated_changes": changes,
        "node_results": {},
    }

    github_service.commit_and_create_pr.side_effect = RuntimeError("failure")
    monkeypatch.setattr(agent, "_generate_branch_name", lambda: "test-branch")

    result = agent.execute(context)

    assert result.success is False
    assert "Failed to submit pull request" in result.message


def test_generate_commit_message_counts_operations(agent):
    changes = [
        FileChange(path="a.md", action=FileAction.CREATE, content=""),
        FileChange(path="b.md", action=FileAction.UPDATE, content=""),
        FileChange(path="c.md", action=FileAction.DELETE),
    ]
    node_results = {
        "article_proposal": {"success": True, "message": "Proposed"},
    }

    message = agent._generate_commit_message("new_article", node_results, changes)

    assert "Automated vault improvements via new_article strategy" in message
    assert "Proposed" in message
    assert "created" in message and "updated" in message and "deleted" in message


def test_generate_pr_content_new_article(agent):
    changes = [FileChange(path="test.md", action=FileAction.CREATE, content="# Test")]
    node_results = {
        "article_proposal": {
            "success": True,
            "message": "Generated article",
            "changes_count": 1,
        }
    }

    title, body = agent._generate_pr_content("new_article", node_results, changes)

    assert title == "Automated vault improvements (new_article)"
    assert "Generated article" in body
    assert "Total Changes" in body
    assert "article_proposal" in body


def test_generate_pr_content_research(agent):
    changes = [
        FileChange(
            path="proposals/topic.md",
            action=FileAction.CREATE,
            content="# Proposal",
        )
    ]
    node_results = {
        "article_proposal": {
            "success": True,
            "message": "Proposed topic",
            "changes_count": 0,
            "metadata": {"topic_title": "AI", "tags": ["ai", "ml"]},
        },
        "deep_research": {
            "success": True,
            "message": "Research complete",
            "changes_count": 1,
            "metadata": {
                "proposal_filename": "ai.md",
                "sources_count": 3,
                "proposal_path": "proposals/ai.md",
            },
        },
    }

    title, body = agent._generate_pr_content("research_proposal", node_results, changes)

    assert title == "Research Proposal: Ai"
    assert "Research Proposal" in body
    assert "**Topic**: AI" in body
    assert "**Tags**: ai, ml" in body
    assert "Sources**: 3 references" in body


def test_generate_branch_name_prefix(agent):
    branch_name = agent._generate_branch_name()
    assert branch_name.startswith("obsidian-agents/workflow-")
