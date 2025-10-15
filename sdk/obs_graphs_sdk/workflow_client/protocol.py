"""Protocol definitions for the workflow client SDK."""

from typing import Protocol

from .schemas import WorkflowRequest, WorkflowResponse


class WorkflowClientProtocol(Protocol):
    """Typed interface for workflow API clients."""

    def run_workflow(
        self, workflow_name: str, payload: WorkflowRequest
    ) -> WorkflowResponse:
        """Execute the named workflow using the provided payload."""
        ...
