"""Unit tests for Celery workflow tasks."""

import shutil
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.v1.models.workflow import Workflow, WorkflowStatus
from src.api.v1.tasks.workflow_tasks import run_workflow_task
from src.db.database import Base
from tests.fixtures.db.workflow_states import create_pending_workflow


# Test database setup
@pytest.fixture
def test_db():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def celery_eager_mode():
    """Configure Celery to run tasks synchronously in eager mode."""
    from src.tasks.celery_app import celery_app

    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
    yield celery_app
    celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)


@pytest.fixture
def temp_vault_path(tmp_path):
    """Create a temporary directory for vault clones."""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    yield vault_path
    # Cleanup
    if vault_path.exists():
        shutil.rmtree(vault_path)


class TestRunWorkflowTask:
    """Tests for run_workflow_task Celery task."""

    @patch("src.api.v1.tasks.workflow_tasks.get_db")
    @patch("src.api.v1.tasks.workflow_tasks.container.get_github_client")
    @patch("src.api.v1.tasks.workflow_tasks.container.get_vault_service")
    @patch("src.api.v1.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_retrieves_workflow_from_database(
        self,
        mock_graph_builder,
        mock_vault_service,
        mock_github_client,
        mock_get_db,
        test_db,
    ):
        """Test that task retrieves workflow record from database."""
        # Setup
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.pr_url = "https://github.com/test/repo/pull/1"
        mock_result.changes = []
        mock_result.summary = "Test summary"
        mock_result.agent_results = {}
        mock_result.branch_name = "test-branch"
        mock_builder_instance.run_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        # Save workflow ID before task execution (session will be closed)
        workflow_id = workflow.id

        # Execute task
        run_workflow_task(workflow_id)

        # Verify workflow was retrieved and updated
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow is not None
        assert updated_workflow.status == WorkflowStatus.COMPLETED
        assert updated_workflow.pr_url == "https://github.com/test/repo/pull/1"

    @patch("src.api.v1.tasks.workflow_tasks.get_db")
    @patch("src.api.v1.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_updates_status_to_running(
        self, mock_graph_builder, mock_get_db, test_db
    ):
        """Test that task updates workflow status to RUNNING at start."""
        workflow = create_pending_workflow(test_db)
        workflow_id = workflow.id
        mock_get_db.return_value = iter([test_db])

        # Mock GraphBuilder to raise error
        mock_builder_instance = MagicMock()
        mock_builder_instance.run_workflow.side_effect = Exception("Stop here")
        mock_graph_builder.return_value = mock_builder_instance

        with pytest.raises(Exception):
            run_workflow_task(workflow_id)

        # Check status was updated to FAILED after exception
        workflow = test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        assert workflow.status == WorkflowStatus.FAILED
        assert workflow.started_at is not None

    @patch("src.api.v1.tasks.workflow_tasks.get_db")
    @patch("src.api.v1.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_calls_run_workflow_and_updates_db(
        self,
        mock_graph_builder,
        mock_get_db,
        test_db,
    ):
        """Test that task calls run_workflow successfully."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.pr_url = "https://github.com/test/repo/pull/1"
        mock_result.changes = []
        mock_result.summary = "Test"
        mock_result.agent_results = {}
        mock_result.branch_name = "test-branch"
        mock_builder_instance.run_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify run_workflow was called
        mock_builder_instance.run_workflow.assert_called_once()

        # Verify workflow is completed
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.status == WorkflowStatus.COMPLETED

    @patch("src.api.v1.tasks.workflow_tasks.get_db")
    @patch("src.api.v1.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_creates_pull_request(
        self,
        mock_graph_builder,
        mock_get_db,
        test_db,
    ):
        """Test that task stores PR URL in database."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Improved articles"
        mock_result.agent_results = {}
        mock_result.pr_url = "https://github.com/test/repo/pull/42"
        mock_result.branch_name = "test-branch"
        mock_builder_instance.run_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify PR URL was stored
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.pr_url == "https://github.com/test/repo/pull/42"

    @patch("src.api.v1.tasks.workflow_tasks.get_db")
    @patch("src.api.v1.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_updates_workflow_to_completed(
        self,
        mock_graph_builder,
        mock_get_db,
        test_db,
    ):
        """Test that task updates workflow to COMPLETED on success."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Success"
        mock_result.agent_results = {}
        mock_result.pr_url = "https://github.com/test/repo/pull/1"
        mock_result.branch_name = "test-branch"
        mock_builder_instance.run_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify workflow is completed
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.status == WorkflowStatus.COMPLETED
        assert updated_workflow.completed_at is not None

    @patch("src.api.v1.tasks.workflow_tasks.get_db")
    @patch("src.api.v1.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_updates_workflow_to_failed_on_error(
        self,
        mock_graph_builder,
        mock_get_db,
        test_db,
    ):
        """Test that task updates workflow to FAILED and stores error message on failure."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_builder_instance.run_workflow.side_effect = Exception("Workflow error")
        mock_graph_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        # Task should handle the exception
        with pytest.raises(Exception):
            run_workflow_task(workflow_id)

        # Verify workflow was marked as failed
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.status == WorkflowStatus.FAILED
        assert updated_workflow.error_message == "Workflow error"
        assert updated_workflow.completed_at is not None

    @patch("src.api.v1.tasks.workflow_tasks.get_db")
    def test_task_raises_error_for_nonexistent_workflow(self, mock_get_db, test_db):
        """Test that task raises error if workflow ID doesn't exist."""
        mock_get_db.return_value = iter([test_db])

        with pytest.raises(Exception) as exc_info:
            run_workflow_task(99999)

        assert "not found" in str(exc_info.value).lower()
