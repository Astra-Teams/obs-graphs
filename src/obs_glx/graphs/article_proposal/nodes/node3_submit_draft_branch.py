"""Node responsible for delegating draft creation directly to GitHub."""

from __future__ import annotations

import re
from pathlib import Path

from src.obs_glx.graphs.article_proposal.state import (
    FileAction,
    FileChange,
    NodeResult,
)
from src.obs_glx.protocols import NodeProtocol
from src.obs_glx.services.github_draft_service import GitHubDraftServiceProtocol


class SubmitDraftBranchNode(NodeProtocol):
    """Transforms accumulated changes into a draft branch via GitHub."""

    name = "submit_draft_branch"

    def __init__(self, draft_service: GitHubDraftServiceProtocol):
        self._draft_service = draft_service

    def validate_input(self, state: dict) -> bool:
        required_keys = ["strategy", "accumulated_changes", "node_results"]
        return all(key in state for key in required_keys)

    # Async for protocol compatibility, no awaitable operations in this method
    async def execute(self, state: dict) -> NodeResult:
        if not self.validate_input(state):
            raise ValueError(
                "Invalid context: strategy, accumulated_changes, and node_results are required"
            )

        accumulated_changes: list[FileChange] = state["accumulated_changes"]

        if not accumulated_changes:
            return NodeResult(
                success=True,
                changes=[],
                message="No changes detected; skipping GitHub submission",
                metadata={"branch_name": ""},
            )

        try:
            draft_change = self._select_draft_change(accumulated_changes)
            file_name = Path(draft_change.path).name
            content = draft_change.content or ""

            drafts = [{"file_name": file_name, "content": content}]
            response = await self._draft_service.create_draft_branch(drafts=drafts)
            if not isinstance(response, str):
                raise ValueError(
                    "GitHub draft service returned unexpected response payload"
                )

            created_branch = response
            if not isinstance(created_branch, str) or not created_branch.strip():
                raise ValueError(
                    "GitHub draft service response is missing a valid branch name"
                )

            message = f"Draft branch created successfully: {created_branch}"

            return NodeResult(
                success=True,
                changes=[],
                message=message,
                metadata={
                    "branch_name": created_branch,
                    "draft_file": draft_change.path,
                },
            )

        except Exception as exc:  # pragma: no cover - handled by workflow logging
            return NodeResult(
                success=False,
                changes=[],
                message=f"Failed to submit draft branch: {exc}",
                metadata={"error": str(exc)},
            )

    def _select_draft_change(self, changes: list[FileChange]) -> FileChange:
        create_changes = [c for c in changes if c.action is FileAction.CREATE]
        if not create_changes:
            raise ValueError("No draft creation detected in accumulated changes.")
        if len(create_changes) > 1:
            raise ValueError("Multiple draft files detected; expected a single draft.")

        draft_change = create_changes[0]
        if not draft_change.content:
            raise ValueError("Draft content is missing for GitHub submission.")

        return draft_change

    def _derive_branch_name(self, file_name: str, node_results: dict) -> str:
        metadata_filename = (
            node_results.get("deep_research", {})
            .get("metadata", {})
            .get("proposal_filename")
        )

        stem_source = metadata_filename or file_name
        stem = Path(stem_source).stem.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
        if not slug:
            slug = "draft"

        return f"draft/{slug}"
