"""End-to-end workflow scenarios covering success, failure, and concurrency."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

import httpx


def _poll_workflow_until_terminal(
    client: httpx.Client,
    workflow_id: int,
    timeout: float = 300.0,
    interval: float = 2.0,
) -> Dict[str, Any]:
    """
    Poll the workflow API endpoint until it reaches a terminal status.

    Args:
        client: HTTP client configured with base URL
        workflow_id: ID of the workflow to poll
        timeout: Maximum time to wait in seconds
        interval: Time between polls in seconds

    Returns:
        The final workflow data dictionary

    Raises:
        TimeoutError: If workflow doesn't reach terminal state within timeout
        httpx.HTTPError: If API request fails
    """
    start_time = time.time()
    terminal_statuses = {"COMPLETED", "FAILED"}

    while time.time() - start_time < timeout:
        response = client.get(f"/api/v1/workflows/{workflow_id}")
        response.raise_for_status()
        workflow_data = response.json()

        status = workflow_data.get("status")
        if status in terminal_statuses:
            return workflow_data

        time.sleep(interval)

    raise TimeoutError(
        f"Workflow {workflow_id} did not reach terminal state within {timeout}s"
    )


class TestWorkflowE2E:
    """Full-stack workflow scenarios executed against the running API service."""

    def test_successful_workflow_lifecycle(self) -> None:
        """
        Execute a workflow end-to-end and verify successful completion.

        This test validates the full workflow lifecycle using only API calls,
        polling until the workflow reaches a terminal state.
        """
        # Submit workflow
        with httpx.Client(base_url="http://127.0.0.1:8002", timeout=30.0) as client:
            response = client.post(
                "/api/v1/workflows/run",
                json={
                    "prompts": ["Create a new article about testing"],
                    "async_execution": True,
                },
            )
            if response.status_code != 201:
                print("\n=== DEBUG: Error Response ===")
                print(f"Status: {response.status_code}")
                print(f"Content: {response.text}")
                print("=============================\n")
            assert response.status_code == 201
            payload = response.json()
            print("\n=== DEBUG: Initial workflow response ===")
            print(f"Payload: {payload}")
            workflow_id = payload["id"]
            assert "id" in payload
            print(f"Status: {payload['status']}")
            print(f"Error message: {payload.get('error_message')}")
            print("===================================\n")
            assert payload["status"] in {"PENDING", "RUNNING"}

            # Poll until terminal state
            workflow_data = _poll_workflow_until_terminal(
                client, workflow_id, timeout=300.0
            )

            print("\n=== DEBUG: Final workflow data ===")
            print(f"Status: {workflow_data['status']}")
            print(f"Error message: {workflow_data.get('error_message')}")
            print("===================================\n")

            # Verify completion
            assert workflow_data["id"] == workflow_id
            assert workflow_data["status"] == "COMPLETED"
            assert workflow_data["branch_name"] is not None
            assert workflow_data["error_message"] is None
            assert "strategy" in workflow_data

            # Verify it appears in the completed workflows list
            list_response = client.get(
                "/api/v1/workflows", params={"status": "COMPLETED", "limit": 10}
            )
            assert list_response.status_code == 200
            list_payload = list_response.json()
            assert any(item["id"] == workflow_id for item in list_payload["workflows"])

    def test_failed_workflow_surfaces_error_details(self) -> None:
        """
        Execute a workflow that fails and verify error diagnostics.

        This test validates that workflow failures are properly captured and
        surfaced through the API with meaningful error messages.
        """
        # Submit workflow with invalid configuration to trigger failure
        with httpx.Client(base_url="http://127.0.0.1:8002", timeout=30.0) as client:
            response = client.post(
                "/api/v1/workflows/run",
                json={
                    "prompts": ["fail intentionally"],
                    "async_execution": True,
                },
            )
            assert response.status_code == 201
            workflow_id = response.json()["id"]

            # Poll until terminal state (expecting FAILED)
            workflow_data = _poll_workflow_until_terminal(
                client, workflow_id, timeout=300.0
            )

            # Verify failure was captured
            assert workflow_data["status"] == "FAILED"
            assert workflow_data["error_message"] is not None
            assert len(workflow_data["error_message"]) > 0
            assert workflow_data["branch_name"] is None

            # Verify it appears in the failed workflows list
            failed_list = client.get(
                "/api/v1/workflows", params={"status": "FAILED", "limit": 10}
            )
            assert failed_list.status_code == 200
            failed_ids = {item["id"] for item in failed_list.json()["workflows"]}
            assert workflow_id in failed_ids

    def test_concurrent_workflow_requests_assign_unique_ids(self) -> None:
        """
        Submit multiple workflows concurrently and verify they are independent.

        This test validates that the API correctly handles concurrent workflow
        submissions, assigning unique IDs and managing each workflow separately.
        """

        def _submit_workflow() -> Dict[str, Any]:
            with httpx.Client(base_url="http://127.0.0.1:8002", timeout=30.0) as client:
                response = client.post(
                    "/api/v1/workflows/run",
                    json={
                        "prompts": ["Concurrent test workflow"],
                        "async_execution": True,
                    },
                )
                assert response.status_code == 201
                return response.json()

        # Submit 3 workflows concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(lambda _: _submit_workflow(), range(3)))

        workflow_ids = {result["id"] for result in results}
        assert len(workflow_ids) == 3, "All workflows should have unique IDs"

        # Verify all workflows are accessible via API
        with httpx.Client(base_url="http://127.0.0.1:8002", timeout=30.0) as client:
            for workflow_id in workflow_ids:
                response = client.get(f"/api/v1/workflows/{workflow_id}")
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == workflow_id
                assert data["status"] in {"PENDING", "RUNNING", "COMPLETED", "FAILED"}
