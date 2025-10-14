"""Unit tests for SubmitPullRequestAgent with obs-gtwy integration."""

from unittest.mock import MagicMock

import pytest

from src.obs_graphs.graphs.article_proposal.nodes.node3_submit_pull_request import (
    SubmitPullRequestAgent,
)
from src.obs_graphs.graphs.article_proposal.state import FileAction, FileChange


@pytest.fixture
def gateway_client():
    client = MagicMock()
    client.create_drafts.return_value = {"branch_name": "draft/sample-branch"}
    return client


@pytest.fixture
def agent(gateway_client):
    return SubmitPullRequestAgent(gateway_client)


def test_validate_input_valid(agent):
    context = {
        "strategy": "research_proposal",
        "accumulated_changes": [],
        "node_results": {},
    }
    assert agent.validate_input(context) is True


def test_validate_input_missing_keys(agent):
    context = {"strategy": "research_proposal"}
    assert agent.validate_input(context) is False


def test_execute_with_no_changes_skips_gateway(agent, gateway_client):
    context = {
        "strategy": "research_proposal",
        "accumulated_changes": [],
        "node_results": {},
    }

    result = agent.execute(context)

    assert result.success is True
    assert result.metadata == {"branch_name": ""}
    gateway_client.create_drafts.assert_not_called()


def test_execute_submits_single_draft(agent, gateway_client):
    change = FileChange(
        path="proposals/sample.md",
        action=FileAction.CREATE,
        content="# Sample Draft",
    )
    context = {
        "strategy": "research_proposal",
        "accumulated_changes": [change],
        "node_results": {
            "deep_research": {
                "metadata": {"proposal_filename": "sample.md"},
                "success": True,
                "message": "Generated draft",
            }
        },
    }

    result = agent.execute(context)

    gateway_client.create_drafts.assert_called_once_with(
        drafts=[{"file_name": "sample.md", "content": "# Sample Draft"}],
        branch_name="draft/sample",
    )
    assert result.success is True
    assert result.metadata["branch_name"] == "draft/sample-branch"
    assert result.metadata["draft_file"] == "proposals/sample.md"


def test_execute_raises_when_multiple_drafts(agent):
    change_a = FileChange(
        path="proposals/a.md",
        action=FileAction.CREATE,
        content="# A",
    )
    change_b = FileChange(
        path="proposals/b.md",
        action=FileAction.CREATE,
        content="# B",
    )

    context = {
        "strategy": "research_proposal",
        "accumulated_changes": [change_a, change_b],
        "node_results": {},
    }

    result = agent.execute(context)

    assert result.success is False
    assert "Multiple draft files detected" in result.message


def test_execute_handles_gateway_exception(agent, gateway_client):
    change = FileChange(
        path="proposals/sample.md",
        action=FileAction.CREATE,
        content="# Sample Draft",
    )
    context = {
        "strategy": "research_proposal",
        "accumulated_changes": [change],
        "node_results": {},
    }

    gateway_client.create_drafts.side_effect = RuntimeError("gateway down")

    result = agent.execute(context)

    assert result.success is False
    assert "gateway down" in result.message


def test_branch_name_derives_from_filename(agent):
    branch = agent._derive_branch_name("My Draft.md", {})
    assert branch == "draft/my-draft"


def test_branch_name_uses_metadata_filename(agent):
    node_results = {"deep_research": {"metadata": {"proposal_filename": "AI.md"}}}
    branch = agent._derive_branch_name("ignored.md", node_results)
    assert branch == "draft/ai"
