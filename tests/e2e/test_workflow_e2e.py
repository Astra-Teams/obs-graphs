"""End-to-end workflow scenarios covering success, failure, and concurrency."""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql import bindparam

_WORKFLOW_UPDATE_DELAY = 1.0  # seconds


def _get_test_db_engine() -> Engine:
    """Return SQLAlchemy engine connected to the test PostgreSQL instance."""
    user = os.getenv("POSTGRES_USER", "user")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    host = os.getenv("HOST_BIND_IP", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_TEST_DB") or os.getenv(
        "POSTGRES_HOST_DB", "obs-graph-test"
    )

    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(url, future=True)


def _update_workflow(workflow_id: int, values: Dict[str, Any]) -> None:
    """Update a workflow row directly in the database."""
    engine = _get_test_db_engine()
    try:
        with engine.begin() as connection:
            assignments = ", ".join(f"{key} = :{key}" for key in values.keys())
            statement = text(
                f"UPDATE workflows SET {assignments} WHERE id = :workflow_id"
            )
            payload = {**values, "workflow_id": workflow_id}
            connection.execute(statement, payload)
    finally:
        engine.dispose()


class TestWorkflowE2E:
    """Full-stack workflow scenarios executed against the running API service."""

    def test_successful_workflow_lifecycle(self, api_base_url: str) -> None:
        """Simulate a successful workflow execution end-to-end."""
        with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
            response = client.post("/api/v1/workflows/run", json={})
            assert response.status_code == 201
            payload = response.json()

            workflow_id = payload["id"]
            # Note: Workflow may fail due to missing GitHub config, but we test the API flow
            # For e2e, we focus on API and DB operations rather than full workflow execution

            # Manually update to COMPLETED to simulate success
            completed_at = datetime.now(timezone.utc)
            metadata = {
                "agent_results": {
                    "new_article": {"success": True, "changes_count": 1},
                    "quality_audit": {"success": True, "changes_count": 0},
                },
                "total_changes": 1,
                "branch_name": f"obsidian-agents/{workflow_id}-new_article",
            }
            _update_workflow(
                workflow_id,
                {
                    "status": "COMPLETED",
                    "strategy": "new_article",
                    "started_at": completed_at - timedelta(minutes=2),
                    "completed_at": completed_at,
                    "pr_url": f"https://github.com/example/repo/pull/{workflow_id}",
                    "error_message": None,
                    "workflow_metadata": json.dumps(metadata),
                },
            )

            time.sleep(_WORKFLOW_UPDATE_DELAY)

            workflow_response = client.get(f"/api/v1/workflows/{workflow_id}")
            assert workflow_response.status_code == 200
            workflow_data = workflow_response.json()

            assert workflow_data["status"] == "COMPLETED"
            assert (
                workflow_data["pr_url"]
                == f"https://github.com/example/repo/pull/{workflow_id}"
            )
            assert workflow_data["strategy"] == "new_article"
            assert workflow_data["error_message"] is None

            list_response = client.get(
                "/api/v1/workflows", params={"status": "COMPLETED", "limit": 5}
            )
            assert list_response.status_code == 200
            list_payload = list_response.json()
            assert any(item["id"] == workflow_id for item in list_payload["workflows"])

    def test_failed_workflow_surfaces_error_details(self, api_base_url: str) -> None:
        """Simulate a workflow that fails during execution and verify diagnostics."""
        with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
            response = client.post("/api/v1/workflows/run", json={})
            assert response.status_code == 201
            workflow_id = response.json()["id"]

            failure_time = datetime.now(timezone.utc)
            error_message = "Workflow execution failed: GitHub API authentication error"
            _update_workflow(
                workflow_id,
                {
                    "status": "FAILED",
                    "strategy": "improvement",
                    "started_at": failure_time - timedelta(minutes=1),
                    "completed_at": failure_time,
                    "pr_url": None,
                    "error_message": error_message,
                    "workflow_metadata": json.dumps({"retry_count": 0}),
                },
            )

            time.sleep(_WORKFLOW_UPDATE_DELAY)

            workflow_response = client.get(f"/api/v1/workflows/{workflow_id}")
            assert workflow_response.status_code == 200
            workflow_data = workflow_response.json()

            assert workflow_data["status"] == "FAILED"
            assert workflow_data["error_message"] == error_message
            assert workflow_data["pr_url"] is None

            failed_list = client.get(
                "/api/v1/workflows", params={"status": "FAILED", "limit": 5}
            )
            assert failed_list.status_code == 200
            failed_ids = {item["id"] for item in failed_list.json()["workflows"]}
            assert workflow_id in failed_ids

    def test_concurrent_workflow_requests_assign_unique_ids(
        self, api_base_url: str
    ) -> None:
        """Queue multiple workflows rapidly and ensure they are independent."""

        def _submit_workflow() -> Dict[str, Any]:
            # Use async execution to avoid waiting for workflow completion
            with httpx.Client(base_url=api_base_url, timeout=10.0) as client:
                response = client.post(
                    "/api/v1/workflows/run", json={"async_execution": True}
                )
                assert response.status_code == 201
                return response.json()

        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(lambda _: _submit_workflow(), range(3)))

        workflow_ids = {result["id"] for result in results}

        assert len(workflow_ids) == 3

        # Verify all workflows exist in database and have Celery task IDs
        engine = _get_test_db_engine()
        try:
            statement = text(
                "SELECT COUNT(*) FROM workflows WHERE id IN :ids AND celery_task_id IS NOT NULL"
            ).bindparams(bindparam("ids", expanding=True))
            with engine.connect() as connection:
                count = connection.execute(
                    statement, {"ids": tuple(workflow_ids)}
                ).scalar_one()
            assert count == 3

            # Verify all workflows are in RUNNING state
            status_statement = text(
                "SELECT COUNT(*) FROM workflows WHERE id IN :ids AND status = 'RUNNING'"
            ).bindparams(bindparam("ids", expanding=True))
            with engine.connect() as connection:
                running_count = connection.execute(
                    status_statement, {"ids": tuple(workflow_ids)}
                ).scalar_one()
            assert running_count == 3
        finally:
            engine.dispose()
