"""Unit tests for Celery workflow tasks."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.obs_glx.db.database import Base
from src.obs_glx.db.models.workflow import Workflow, WorkflowStatus
from tests.db.conftest import create_pending_workflow
from worker.obs_glx_worker.tasks import run_workflow_task


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
    from worker.obs_glx_worker.app import celery_app

    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
    yield celery_app
    celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)


class TestRunWorkflowTask:
    """Tests for run_workflow_task Celery task."""

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_retrieves_workflow_from_database(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task retrieves workflow record from database."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        # Setup
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Test summary"
        mock_result.branch_name = "test-branch"
        mock_result.node_results = {}

        async def mock_run_workflow(request, progress_callback=None):
            return mock_result

        mock_builder_instance.run_workflow = MagicMock(side_effect=mock_run_workflow)
        mock_get_builder.return_value = mock_builder_instance

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
        assert updated_workflow.branch_name == "test-branch"

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_updates_status_to_running(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task updates workflow status to RUNNING at start."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        workflow = create_pending_workflow(test_db)
        workflow_id = workflow.id
        mock_get_db.return_value = iter([test_db])

        # Mock ObsidianArticleProposalToPRGraph to raise error
        mock_builder_instance = MagicMock()

        async def mock_run_workflow_with_error(request, progress_callback=None):
            raise Exception("Stop here")

        mock_builder_instance.run_workflow = MagicMock(
            side_effect=mock_run_workflow_with_error
        )
        mock_get_builder.return_value = mock_builder_instance

        with pytest.raises(Exception):
            run_workflow_task(workflow_id)

        # Check status was updated to FAILED after exception
        workflow = test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        assert workflow.status == WorkflowStatus.FAILED
        assert workflow.started_at is not None

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_calls_run_workflow_and_updates_db(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task calls run_workflow successfully."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Test"
        mock_result.branch_name = "test-branch"
        mock_result.node_results = {}

        async def mock_run_workflow(request, progress_callback=None):
            return mock_result

        mock_builder_instance.run_workflow = MagicMock(side_effect=mock_run_workflow)
        mock_get_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify run_workflow was called
        mock_builder_instance.run_workflow.assert_called_once()

        # Verify workflow is completed
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.status == WorkflowStatus.COMPLETED

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_records_branch_name(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task stores branch name in the database."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Improved articles"
        mock_result.branch_name = "test-branch"
        mock_result.node_results = {}

        async def mock_run_workflow(request, progress_callback=None):
            return mock_result

        mock_builder_instance.run_workflow = MagicMock(side_effect=mock_run_workflow)
        mock_get_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify branch name was stored
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.branch_name == "test-branch"

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_updates_workflow_to_completed(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task updates workflow to COMPLETED on success."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Success"
        mock_result.branch_name = "test-branch"
        mock_result.node_results = {}

        async def mock_run_workflow(request, progress_callback=None):
            return mock_result

        mock_builder_instance.run_workflow = MagicMock(side_effect=mock_run_workflow)
        mock_get_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify workflow is completed
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.status == WorkflowStatus.COMPLETED
        assert updated_workflow.completed_at is not None

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_updates_workflow_to_failed_on_error(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task updates workflow to FAILED and stores error message on failure."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()

        async def mock_run_workflow_with_error(request, progress_callback=None):
            raise Exception("Workflow error")

        mock_builder_instance.run_workflow = MagicMock(
            side_effect=mock_run_workflow_with_error
        )
        mock_get_builder.return_value = mock_builder_instance

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

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    def test_task_raises_error_for_nonexistent_workflow(
        self, mock_get_db, mock_prepare_dir, test_db
    ):
        """Test that task raises error if workflow ID doesn't exist."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        mock_get_db.return_value = iter([test_db])

        with pytest.raises(Exception) as exc_info:
            run_workflow_task(99999)

        assert "not found" in str(exc_info.value).lower()

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_propagates_prompt_to_workflow_request(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task propagates prompt from workflow record to WorkflowRunRequest."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        # Create workflow with prompt
        workflow = Workflow(
            workflow_type="article-proposal",
            prompt=["Test research prompt for propagation"],
            status=WorkflowStatus.PENDING,
            strategy=None,
        )
        test_db.add(workflow)
        test_db.commit()
        test_db.refresh(workflow)

        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Success"
        mock_result.branch_name = "test-branch"
        mock_result.node_results = {}

        async def mock_run_workflow(request, progress_callback=None):
            return mock_result

        mock_builder_instance.run_workflow = MagicMock(side_effect=mock_run_workflow)
        mock_get_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify run_workflow was called with request containing prompt
        mock_builder_instance.run_workflow.assert_called_once()
        call_args = mock_builder_instance.run_workflow.call_args[0]
        request = call_args[0]

        assert hasattr(request, "prompts")
        assert request.prompts == ["Test research prompt for propagation"]
        assert request.primary_prompt == "Test research prompt for propagation"

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_propagates_empty_prompt_when_null(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task propagates empty string when workflow prompt is NULL."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        # Create workflow with NULL prompt (old records)
        workflow = Workflow(
            workflow_type="article-proposal",
            prompt=None,
            status=WorkflowStatus.PENDING,
            strategy=None,
        )
        test_db.add(workflow)
        test_db.commit()
        test_db.refresh(workflow)

        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Success"
        mock_result.branch_name = "test-branch"
        mock_result.node_results = {}

        async def mock_run_workflow(request, progress_callback=None):
            return mock_result

        mock_builder_instance.run_workflow = MagicMock(side_effect=mock_run_workflow)
        mock_get_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify run_workflow was called with empty prompt
        mock_builder_instance.run_workflow.assert_called_once()
        call_args = mock_builder_instance.run_workflow.call_args[0]
        request = call_args[0]

        assert hasattr(request, "prompts")
        assert request.prompts == ["Default research prompt"]
        assert request.primary_prompt == "Default research prompt"

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_propagates_prompt_with_strategy(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Test that task propagates both prompt and strategy to WorkflowRunRequest."""
        mock_prepare_dir.return_value = Path("/tmp/vault")
        from src.obs_glx.graphs.article_proposal.state import WorkflowStrategy

        # Create workflow with prompt and strategy
        workflow = Workflow(
            workflow_type="article-proposal",
            prompt=["Research quantum computing"],
            status=WorkflowStatus.PENDING,
            strategy=WorkflowStrategy.RESEARCH_PROPOSAL,
        )
        test_db.add(workflow)
        test_db.commit()
        test_db.refresh(workflow)

        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Success"
        mock_result.branch_name = "test-branch"
        mock_result.node_results = {}

        async def mock_run_workflow(request, progress_callback=None):
            return mock_result

        mock_builder_instance.run_workflow = MagicMock(side_effect=mock_run_workflow)
        mock_get_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        # Verify run_workflow was called with both prompt and strategy
        mock_builder_instance.run_workflow.assert_called_once()
        call_args = mock_builder_instance.run_workflow.call_args[0]
        request = call_args[0]

        assert request.prompts == ["Research quantum computing"]
        assert request.primary_prompt == "Research quantum computing"
        assert request.strategy == WorkflowStrategy.RESEARCH_PROPOSAL

    @patch("worker.obs_glx_worker.tasks._prepare_workflow_directory")
    @patch("worker.obs_glx_worker.tasks.get_db")
    @patch("src.obs_glx.graphs.factory.get_graph_builder")
    def test_task_propagates_prompt_from_metadata(
        self,
        mock_get_builder,
        mock_get_db,
        mock_prepare_dir,
        test_db,
    ):
        """Task should propagate prompts from workflow metadata."""
        mock_prepare_dir.return_value = Path("/tmp/vault")

        workflow = Workflow(
            workflow_type="article-proposal",
            prompt=["Backend specific prompt"],
            status=WorkflowStatus.PENDING,
            strategy=None,
            workflow_metadata={"backend": "mlx"},
        )
        test_db.add(workflow)
        test_db.commit()
        test_db.refresh(workflow)

        mock_get_db.return_value = iter([test_db])

        mock_builder_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Success"
        mock_result.branch_name = "test-branch"
        mock_result.node_results = {}

        async def mock_run_workflow(request, progress_callback=None):
            return mock_result

        mock_builder_instance.run_workflow = MagicMock(side_effect=mock_run_workflow)
        mock_get_builder.return_value = mock_builder_instance

        workflow_id = workflow.id

        run_workflow_task(workflow_id)

        mock_builder_instance.run_workflow.assert_called_once()
        request = mock_builder_instance.run_workflow.call_args[0][0]
        assert request.prompts == ["Backend specific prompt"]
