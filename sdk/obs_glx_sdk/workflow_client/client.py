"""HTTP client for interacting with the obs-graphs workflow API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import httpx

from .schemas import WorkflowRequest, WorkflowResponse

if TYPE_CHECKING:
    from .protocol import WorkflowClientProtocol


class WorkflowApiClient:
    """Synchronous client that wraps the obs-graphs workflow endpoints."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        *,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)
        self._owns_client = client is None

    def run_workflow(
        self, workflow_name: str, payload: WorkflowRequest
    ) -> WorkflowResponse:
        """Execute a workflow by name and parse the structured response."""

        url = f"/api/workflows/{workflow_name}/run"
        body = payload.model_dump()
        response = self._client.post(url, json=body)
        response.raise_for_status()
        data = response.json()
        return WorkflowResponse(**data)

    def close(self) -> None:
        """Close the underlying HTTP client when this instance owns it."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "WorkflowApiClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


if TYPE_CHECKING:
    # Static interface check to guarantee protocol compatibility during type checking
    _: WorkflowClientProtocol = WorkflowApiClient(base_url="http://localhost")
