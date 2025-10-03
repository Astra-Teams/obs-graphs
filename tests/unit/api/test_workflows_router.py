"""Unit tests for workflow API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.database import Base, get_db
from src.db.models.workflow import Workflow, WorkflowStatus
from src.main import app
from tests.fixtures.db.workflow_states import (
    create_completed_workflow,
    create_failed_workflow,
    create_pending_workflow,
    create_running_workflow,
)


# Test database setup
@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_db(test_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_engine):
    """Create a test client with mocked database dependency."""
    TestingSessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestWorkflowRunEndpoint:
    """Tests for POST /api/v1/workflows/run endpoint."""

    @patch("src.api.v1.routers.workflows.run_workflow_task")
    def test_run_workflow_creates_pending_workflow(
        self, mock_task_module, client, test_db
    ):
        """Test that POST /workflows/run creates a workflow with PENDING status."""
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.id = "test-celery-task-123"
        mock_task_module.delay.return_value = mock_task

        # Make request
        response = client.post("/api/v1/workflows/run")

        # Assert response
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "PENDING"
        assert data["celery_task_id"] == "test-celery-task-123"
        assert "Workflow" in data["message"]
        assert "queued" in data["message"]

        # Verify workflow was created in database
        workflow = test_db.query(Workflow).filter(Workflow.id == data["id"]).first()
        assert workflow is not None
        assert workflow.status == WorkflowStatus.PENDING
        assert workflow.celery_task_id == "test-celery-task-123"

    @patch("src.api.v1.routers.workflows.run_workflow_task")
    def test_run_workflow_with_strategy_parameter(
        self, mock_task_module, client, test_db
    ):
        """Test that POST /workflows/run accepts optional strategy parameter."""
        mock_task = MagicMock()
        mock_task.id = "test-task-456"
        mock_task_module.delay.return_value = mock_task

        # Make request with strategy
        response = client.post(
            "/api/v1/workflows/run", json={"strategy": "new_article"}
        )

        assert response.status_code == 201
        data = response.json()

        # Verify workflow has strategy set
        workflow = test_db.query(Workflow).filter(Workflow.id == data["id"]).first()
        assert workflow.strategy == "new_article"

    @patch("src.api.v1.routers.workflows.run_workflow_task")
    def test_run_workflow_dispatches_celery_task(
        self, mock_task_module, client, test_db
    ):
        """Test that workflow run dispatches Celery task with workflow ID."""
        mock_task = MagicMock()
        mock_task.id = "task-789"
        mock_task_module.delay.return_value = mock_task

        response = client.post("/api/v1/workflows/run")
        assert response.status_code == 201

        workflow_id = response.json()["id"]

        # Verify Celery task was dispatched with correct workflow ID
        mock_task_module.delay.assert_called_once_with(workflow_id)

    @patch("src.api.v1.routers.workflows.run_workflow_task")
    def test_run_workflow_stores_celery_task_id(
        self, mock_task_module, client, test_db
    ):
        """Test that Celery task ID is stored in workflow record."""
        mock_task = MagicMock()
        mock_task.id = "stored-task-id"
        mock_task_module.delay.return_value = mock_task

        response = client.post("/api/v1/workflows/run")
        workflow_id = response.json()["id"]

        workflow = test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        assert workflow.celery_task_id == "stored-task-id"

    @patch("src.api.v1.routers.workflows.run_workflow_task")
    def test_run_workflow_returns_201_status(self, mock_task_module, client):
        """Test that successful workflow creation returns 201 Created."""
        mock_task = MagicMock()
        mock_task.id = "task-id"
        mock_task_module.delay.return_value = mock_task

        response = client.post("/api/v1/workflows/run")
        assert response.status_code == 201


class TestGetWorkflowEndpoint:
    """Tests for GET /api/v1/workflows/{workflow_id} endpoint."""

    def test_get_workflow_returns_correct_workflow(self, client, test_db):
        """Test that GET /workflows/{id} returns correct workflow details."""
        # Create test workflow
        workflow = create_pending_workflow(test_db)

        response = client.get(f"/api/v1/workflows/{workflow.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workflow.id
        assert data["status"] == "PENDING"

    def test_get_workflow_returns_404_for_nonexistent(self, client, test_db):
        """Test that GET /workflows/{id} returns 404 for non-existent workflow."""
        response = client.get("/api/v1/workflows/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_completed_workflow_includes_pr_url(self, client, test_db):
        """Test that completed workflow response includes PR URL."""
        workflow = create_completed_workflow(test_db, with_pr_url=True)

        response = client.get(f"/api/v1/workflows/{workflow.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["pr_url"] is not None
        assert "github.com" in data["pr_url"]

    def test_get_failed_workflow_includes_error_message(self, client, test_db):
        """Test that failed workflow response includes error message."""
        workflow = create_failed_workflow(test_db, with_error_message=True)

        response = client.get(f"/api/v1/workflows/{workflow.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILED"
        assert data["error_message"] is not None
        assert len(data["error_message"]) > 0

    def test_get_workflow_includes_timestamps(self, client, test_db):
        """Test that workflow response includes created_at timestamp."""
        workflow = create_running_workflow(test_db)

        response = client.get(f"/api/v1/workflows/{workflow.id}")

        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data
        assert data["created_at"] is not None
        assert "started_at" in data
        assert data["started_at"] is not None


class TestListWorkflowsEndpoint:
    """Tests for GET /api/v1/workflows endpoint."""

    def test_list_workflows_returns_paginated_results(self, client, test_db):
        """Test that GET /workflows returns paginated list of workflows."""
        # Create multiple workflows
        for _ in range(5):
            create_pending_workflow(test_db)

        response = client.get("/api/v1/workflows?limit=3&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert len(data["workflows"]) == 3
        assert data["total"] == 5
        assert data["limit"] == 3
        assert data["offset"] == 0

    def test_list_workflows_filters_by_status(self, client, test_db):
        """Test that GET /workflows filters by status query parameter."""
        # Create workflows with different statuses
        create_pending_workflow(test_db)
        create_running_workflow(test_db)
        create_completed_workflow(test_db)
        create_failed_workflow(test_db)

        # Filter by completed status
        response = client.get("/api/v1/workflows?status=COMPLETED")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert all(w["status"] == "COMPLETED" for w in data["workflows"])

    def test_list_workflows_returns_400_for_invalid_status(self, client, test_db):
        """Test that invalid status parameter returns 400 error."""
        response = client.get("/api/v1/workflows?status=invalid_status")

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_list_workflows_pagination_offset(self, client, test_db):
        """Test that pagination offset works correctly."""
        # Create 5 workflows
        for _ in range(5):
            create_pending_workflow(test_db)

        # Get first page
        response1 = client.get("/api/v1/workflows?limit=2&offset=0")
        data1 = response1.json()

        # Get second page
        response2 = client.get("/api/v1/workflows?limit=2&offset=2")
        data2 = response2.json()

        # Verify different results
        assert len(data1["workflows"]) == 2
        assert len(data2["workflows"]) == 2
        assert data1["workflows"][0]["id"] != data2["workflows"][0]["id"]

    def test_list_workflows_orders_by_created_at_desc(self, client, test_db):
        """Test that workflows are ordered by created_at descending (newest first)."""

        # Create workflows with different timestamps
        old_workflow = create_pending_workflow(
            test_db, created_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        new_workflow = create_pending_workflow(
            test_db, created_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )

        response = client.get("/api/v1/workflows")

        data = response.json()
        # Newest should be first
        assert data["workflows"][0]["id"] == new_workflow.id
        assert data["workflows"][1]["id"] == old_workflow.id

    def test_list_workflows_respects_limit_bounds(self, client, test_db):
        """Test that limit parameter enforces min/max bounds."""
        create_pending_workflow(test_db)

        # Test min bound (should use 1)
        response = client.get("/api/v1/workflows?limit=0")
        assert response.status_code == 422  # Validation error

        # Test max bound (should use 100)
        response = client.get("/api/v1/workflows?limit=101")
        assert response.status_code == 422  # Validation error

    def test_list_workflows_empty_result(self, client, test_db):
        """Test that empty database returns empty list."""
        response = client.get("/api/v1/workflows")

        assert response.status_code == 200
        data = response.json()
        assert data["workflows"] == []
        assert data["total"] == 0
