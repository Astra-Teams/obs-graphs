"""Unit tests for SubmitDraftBranchNode with GitHub integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.obs_glx.graphs.article_proposal.nodes.node3_submit_draft_branch import (
    SubmitDraftBranchNode,
)
from src.obs_glx.graphs.article_proposal.state import FileAction, FileChange


@pytest.fixture
def draft_service():
    service = MagicMock()
    service.create_draft_branch = AsyncMock(
        return_value="drafts/20250101-120000-mock-branch-name"
    )
    return service


@pytest.fixture
def node(draft_service):
    return SubmitDraftBranchNode(draft_service)


def test_validate_input_valid(node):
    context = {
        "strategy": "research_proposal",
        "accumulated_changes": [],
        "node_results": {},
    }
    assert node.validate_input(context) is True


def test_validate_input_missing_keys(node):
    context = {"strategy": "research_proposal"}
    assert node.validate_input(context) is False


@pytest.mark.asyncio
async def test_execute_with_no_changes_skips_service(node, draft_service):
    context = {
        "strategy": "research_proposal",
        "accumulated_changes": [],
        "node_results": {},
    }

    result = await node.execute(context)

    assert result.success is True
    assert result.metadata == {"branch_name": ""}
    draft_service.create_draft_branch.assert_not_called()


@pytest.mark.asyncio
async def test_execute_submits_single_draft(node, draft_service):
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

    result = await node.execute(context)

    draft_service.create_draft_branch.assert_called_once_with(
        drafts=[{"file_name": "sample.md", "content": "# Sample Draft"}],
    )
    assert result.success is True
    assert result.metadata["branch_name"] == "drafts/20250101-120000-mock-branch-name"
    assert result.metadata["draft_file"] == "proposals/sample.md"


@pytest.mark.asyncio
async def test_execute_raises_when_multiple_drafts(node):
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

    result = await node.execute(context)

    assert result.success is False
    assert "Multiple draft files detected" in result.message


@pytest.mark.asyncio
async def test_execute_handles_service_exception(node, draft_service):
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

    draft_service.create_draft_branch.side_effect = RuntimeError("github down")

    result = await node.execute(context)

    assert result.success is False
    assert "github down" in result.message


def test_branch_name_derives_from_filename(node):
    branch = node._derive_branch_name("My Draft.md", {})
    assert branch == "draft/my-draft"


def test_branch_name_uses_metadata_filename(node):
    node_results = {"deep_research": {"metadata": {"proposal_filename": "AI.md"}}}
    branch = node._derive_branch_name("ignored.md", node_results)
    assert branch == "draft/ai"
