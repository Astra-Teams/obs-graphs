"""Agent responsible for delegating draft creation to the obs-gtwy gateway."""

from __future__ import annotations

import re
from pathlib import Path

from obs_gtwy_sdk import GatewayClientProtocol

from src.obs_graphs.graphs.article_proposal.state import (
    AgentResult,
    FileAction,
    FileChange,
)
from src.obs_graphs.protocols import NodeProtocol


class SubmitPullRequestAgent(NodeProtocol):
    """Transforms accumulated changes into a draft branch via obs-gtwy."""

    name = "submit_pull_request"

    def __init__(self, gateway_client: GatewayClientProtocol):
        self._gateway_client = gateway_client

    def validate_input(self, context: dict) -> bool:
        required_keys = ["strategy", "accumulated_changes", "node_results"]
        return all(key in context for key in required_keys)

    def execute(self, context: dict) -> AgentResult:
        if not self.validate_input(context):
            raise ValueError(
                "Invalid context: strategy, accumulated_changes, and node_results are required"
            )

        accumulated_changes: list[FileChange] = context["accumulated_changes"]
        node_results: dict = context["node_results"]

        if not accumulated_changes:
            return AgentResult(
                success=True,
                changes=[],
                message="No changes detected; skipping gateway submission",
                metadata={"branch_name": ""},
            )

        try:
            draft_change = self._select_draft_change(accumulated_changes)
            file_name = Path(draft_change.path).name
            content = draft_change.content or ""

            suggested_branch = self._derive_branch_name(file_name, node_results)
            drafts = [{"file_name": file_name, "content": content}]
            response = self._gateway_client.create_drafts(drafts=drafts)
            if not isinstance(response, dict):
                raise ValueError("obs-gtwy SDK returned unexpected response payload")

            created_branch = response.get("branch_name")
            if not isinstance(created_branch, str) or not created_branch.strip():
                created_branch = suggested_branch

            message = f"Draft branch created successfully: {created_branch}"

            return AgentResult(
                success=True,
                changes=[],
                message=message,
                metadata={
                    "branch_name": created_branch,
                    "draft_file": draft_change.path,
                },
            )

        except Exception as exc:  # pragma: no cover - handled by workflow logging
            return AgentResult(
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
            raise ValueError("Draft content is missing for gateway submission.")

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
