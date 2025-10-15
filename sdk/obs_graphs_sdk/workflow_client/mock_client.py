"""Mock implementation of the workflow API client for local testing."""

from __future__ import annotations

from typing import Any, Dict, List

from .protocol import WorkflowClientProtocol
from .schemas import WorkflowRequest, WorkflowResponse


class MockWorkflowApiClient:
    """In-memory client that simulates workflow execution responses."""

    def __init__(self, base_url: str = "http://mock.test") -> None:
        self.base_url = base_url
        self.call_history: List[Dict[str, Any]] = []

    def run_workflow(
        self, workflow_name: str, payload: WorkflowRequest
    ) -> WorkflowResponse:
        """Store the call arguments and return a deterministic success response."""

        self.call_history.append(
            {
                "workflow_name": workflow_name,
                "payload": payload,
            }
        )
        return WorkflowResponse(
            id=1,
            status="COMPLETED",
            message=f"Workflow '{workflow_name}' completed successfully.",
            celery_task_id=None,
        )


# Interface check for static type analysis
_: WorkflowClientProtocol = MockWorkflowApiClient()
