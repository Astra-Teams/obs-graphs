"""Unit tests for Celery workflow tasks."""

import shutil
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.database import Base
from src.db.models.workflow import Workflow, WorkflowStatus
from src.tasks.workflow_tasks import run_workflow_task
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

    @patch("src.tasks.workflow_tasks.get_db")
    @patch("src.tasks.workflow_tasks.container.get_github_client")
    @patch("src.tasks.workflow_tasks.container.get_vault_service")
    @patch("src.tasks.workflow_tasks.container.get_graph_builder")
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

        # Mock services to prevent actual execution
        mock_github_instance = MagicMock()
        mock_github_instance.commit_and_push.return_value = True
        mock_github_client.return_value = mock_github_instance

        mock_vault_instance = MagicMock()
        mock_vault_instance.validate_vault_structure.return_value = True
        mock_vault_service.return_value = mock_vault_instance

        mock_builder_instance = MagicMock()
        mock_plan = MagicMock()
        mock_plan.strategy = "new_article"
        mock_builder_instance.analyze_vault.return_value = mock_plan

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Test summary"
        mock_result.agent_results = {}
        mock_builder_instance.execute_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/test/repo/pull/1"
        mock_github_instance.create_pull_request.return_value = mock_pr

        # Save workflow ID before task execution (session will be closed)
        workflow_id = workflow.id

        # Execute task
        with patch("src.tasks.workflow_tasks.settings") as mock_settings:
            mock_settings.WORKFLOW_CLONE_BASE_PATH = "/tmp/test"
            mock_settings.GITHUB_REPO_FULL_NAME = "test/repo"
            mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"

            run_workflow_task(workflow_id)

        # Verify workflow was retrieved
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow is not None

    @patch("src.tasks.workflow_tasks.get_db")
    @patch("src.tasks.workflow_tasks.container.get_github_client")
    def test_task_updates_status_to_running(
        self, mock_github_client, mock_get_db, test_db
    ):
        """Test that task updates workflow status to RUNNING at start."""
        workflow = create_pending_workflow(test_db)
        workflow_id = workflow.id
        mock_get_db.return_value = iter([test_db])

        # Mock GitHubService instance to raise error after initialization
        mock_gh_instance = MagicMock()
        mock_gh_instance.clone_repository.side_effect = Exception("Stop here")
        mock_github_client.return_value = mock_gh_instance

        with pytest.raises(Exception):
            run_workflow_task(workflow_id)

        # Check status was updated to RUNNING before failure
        workflow = test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        assert (
            workflow.status == WorkflowStatus.FAILED
        )  # Should be FAILED after exception
        assert workflow.started_at is not None

    @patch("src.tasks.workflow_tasks.get_db")
    @patch("src.tasks.workflow_tasks.container.get_github_client")
    @patch("src.tasks.workflow_tasks.container.get_vault_service")
    @patch("src.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_clones_repository(
        self,
        mock_graph_builder,
        mock_vault_service,
        mock_github_client,
        mock_get_db,
        test_db,
    ):
        """Test that task clones repository to temporary directory."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_github_instance = MagicMock()
        mock_github_instance.commit_and_push.return_value = True
        mock_github_client.return_value = mock_github_instance

        mock_vault_instance = MagicMock()
        mock_vault_instance.validate_vault_structure.return_value = True
        mock_vault_service.return_value = mock_vault_instance

        mock_builder_instance = MagicMock()
        mock_plan = MagicMock()
        mock_plan.strategy = "improvement"
        mock_builder_instance.analyze_vault.return_value = mock_plan

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Test"
        mock_result.agent_results = {}
        mock_builder_instance.execute_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/test/repo/pull/1"
        mock_github_instance.create_pull_request.return_value = mock_pr

        workflow_id = workflow.id

        with patch("src.tasks.workflow_tasks.settings") as mock_settings:
            mock_settings.WORKFLOW_CLONE_BASE_PATH = "/tmp/test"
            mock_settings.GITHUB_REPO_FULL_NAME = "test/repo"
            mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"

            run_workflow_task(workflow_id)

        # Verify clone_repository was called without repo_url argument
        mock_github_instance.clone_repository.assert_called_once()
        call_args = mock_github_instance.clone_repository.call_args
        # Ensure repo_url is not in the call arguments
        assert "repo_url" not in call_args.kwargs

    @patch("src.tasks.workflow_tasks.get_db")
    @patch("src.tasks.workflow_tasks.container.get_github_client")
    @patch("src.tasks.workflow_tasks.container.get_vault_service")
    @patch("src.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_calls_orchestrator_and_applies_changes(
        self,
        mock_graph_builder,
        mock_vault_service,
        mock_github_client,
        mock_get_db,
        test_db,
    ):
        """Test that task calls WorkflowOrchestrator and applies changes."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_github_instance = MagicMock()
        mock_github_instance.commit_and_push.return_value = True
        mock_github_client.return_value = mock_github_instance

        mock_vault_instance = MagicMock()
        mock_vault_instance.validate_vault_structure.return_value = True
        mock_vault_service.return_value = mock_vault_instance

        mock_builder_instance = MagicMock()
        mock_plan = MagicMock()
        mock_plan.strategy = "new_article"
        mock_builder_instance.analyze_vault.return_value = mock_plan

        mock_changes = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = mock_changes
        mock_result.summary = "Created 2 articles"
        mock_result.agent_results = {
            "new_article": {
                "success": True,
                "message": "Created 2 articles",
                "changes_count": 2,
            }
        }
        mock_builder_instance.execute_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/test/repo/pull/1"
        mock_github_instance.create_pull_request.return_value = mock_pr

        workflow_id = workflow.id

        with patch("src.tasks.workflow_tasks.settings") as mock_settings:
            mock_settings.WORKFLOW_CLONE_BASE_PATH = "/tmp/test"
            mock_settings.GITHUB_REPO_FULL_NAME = "test/repo"
            mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"

            run_workflow_task(workflow_id)

        # Verify orchestrator was called
        mock_builder_instance.analyze_vault.assert_called_once()
        mock_builder_instance.execute_workflow.assert_called_once()

        # Verify changes were applied
        mock_vault_instance.apply_changes.assert_called_once()
        assert mock_vault_instance.apply_changes.call_args[0][1] == mock_changes

    @patch("src.tasks.workflow_tasks.get_db")
    @patch("src.tasks.workflow_tasks.container.get_github_client")
    @patch("src.tasks.workflow_tasks.container.get_vault_service")
    @patch("src.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_creates_pull_request(
        self,
        mock_graph_builder,
        mock_vault_service,
        mock_github_client,
        mock_get_db,
        test_db,
    ):
        """Test that task creates PR and stores URL in database."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        mock_github_instance = MagicMock()
        mock_github_instance.commit_and_push.return_value = True
        mock_github_client.return_value = mock_github_instance

        mock_vault_instance = MagicMock()
        mock_vault_instance.validate_vault_structure.return_value = True
        mock_vault_service.return_value = mock_vault_instance

        mock_builder_instance = MagicMock()
        mock_plan = MagicMock()
        mock_plan.strategy = "improvement"
        mock_builder_instance.analyze_vault.return_value = mock_plan

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Improved articles"
        mock_result.agent_results = {}
        mock_builder_instance.execute_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        expected_pr_url = "https://github.com/test/repo/pull/42"
        mock_pr = MagicMock()
        mock_pr.html_url = expected_pr_url
        mock_github_instance.create_pull_request.return_value = mock_pr

        workflow_id = workflow.id

        with patch("src.tasks.workflow_tasks.settings") as mock_settings:
            mock_settings.WORKFLOW_CLONE_BASE_PATH = "/tmp/test"
            mock_settings.GITHUB_REPO_FULL_NAME = "test/repo"
            mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"

            run_workflow_task(workflow_id)

        # Verify PR was created
        mock_github_instance.create_pull_request.assert_called_once()

        # Verify PR URL was stored
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.pr_url == expected_pr_url

    @patch("src.tasks.workflow_tasks.get_db")
    @patch("src.tasks.workflow_tasks.container.get_github_client")
    @patch("src.tasks.workflow_tasks.container.get_vault_service")
    @patch("src.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_updates_workflow_to_completed(
        self,
        mock_graph_builder,
        mock_vault_service,
        mock_github_client,
        mock_get_db,
        test_db,
    ):
        """Test that task updates workflow to COMPLETED on success."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        # Setup all mocks for successful execution
        mock_github_instance = MagicMock()
        mock_github_instance.commit_and_push.return_value = True
        mock_github_client.return_value = mock_github_instance

        mock_vault_instance = MagicMock()
        mock_vault_instance.validate_vault_structure.return_value = True
        mock_vault_service.return_value = mock_vault_instance

        mock_builder_instance = MagicMock()
        mock_plan = MagicMock()
        mock_plan.strategy = "new_article"
        mock_builder_instance.analyze_vault.return_value = mock_plan

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Success"
        mock_result.agent_results = {}
        mock_builder_instance.execute_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/test/repo/pull/1"
        mock_github_instance.create_pull_request.return_value = mock_pr

        workflow_id = workflow.id

        with patch("src.tasks.workflow_tasks.settings") as mock_settings:
            mock_settings.WORKFLOW_CLONE_BASE_PATH = "/tmp/test"
            mock_settings.GITHUB_REPO_FULL_NAME = "test/repo"
            mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"

            run_workflow_task(workflow_id)

        # Verify workflow is completed
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.status == WorkflowStatus.COMPLETED
        assert updated_workflow.completed_at is not None

    @patch("src.tasks.workflow_tasks.get_db")
    @patch("src.tasks.workflow_tasks.container.get_github_client")
    @patch("src.tasks.workflow_tasks.container.get_vault_service")
    @patch("src.tasks.workflow_tasks.container.get_graph_builder")
    def test_task_updates_workflow_to_failed_on_error(
        self,
        mock_graph_builder,
        mock_vault_service,
        mock_github_client,
        mock_get_db,
        test_db,
    ):
        """Test that task updates workflow to FAILED and stores error message on failure."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        # Mock services properly first
        mock_vault_instance = MagicMock()
        mock_vault_service.return_value = mock_vault_instance

        mock_builder_instance = MagicMock()
        mock_graph_builder.return_value = mock_builder_instance

        # Mock GitHub service to raise an error
        mock_github_instance = MagicMock()
        mock_github_instance.clone_repository.side_effect = Exception(
            "GitHub API error"
        )
        mock_github_client.return_value = mock_github_instance

        workflow_id = workflow.id

        with patch("src.tasks.workflow_tasks.settings") as mock_settings:
            mock_settings.WORKFLOW_CLONE_BASE_PATH = "/tmp/test"
            mock_settings.GITHUB_REPO_FULL_NAME = "test/repo"
            mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"

            # Task should handle the exception
            with pytest.raises(Exception):
                run_workflow_task(workflow_id)

        # Verify workflow was marked as failed
        updated_workflow = (
            test_db.query(Workflow).filter(Workflow.id == workflow_id).first()
        )
        assert updated_workflow.status == WorkflowStatus.FAILED
        assert updated_workflow.error_message is not None
        assert "GitHub API error" in updated_workflow.error_message
        assert updated_workflow.completed_at is not None

    @patch("src.tasks.workflow_tasks.get_db")
    @patch("src.tasks.workflow_tasks.container.get_github_client")
    @patch("src.tasks.workflow_tasks.container.get_vault_service")
    @patch("src.tasks.workflow_tasks.container.get_graph_builder")
    @patch("src.tasks.workflow_tasks.shutil.rmtree")
    @patch("src.tasks.workflow_tasks.Path")
    def test_task_cleans_up_temporary_directory(
        self,
        mock_path,
        mock_rmtree,
        mock_graph_builder,
        mock_vault_service,
        mock_github_client,
        mock_get_db,
        test_db,
    ):
        """Test that task cleans up temporary directory in all cases."""
        workflow = create_pending_workflow(test_db)
        mock_get_db.return_value = iter([test_db])

        # Mock Path to return a path that exists
        mock_temp_path = MagicMock()
        mock_temp_path.exists.return_value = True
        mock_path.return_value = mock_temp_path
        # Make Path() / operator work
        mock_path.return_value.__truediv__ = lambda self, x: mock_temp_path

        mock_github_instance = MagicMock()
        mock_github_instance.commit_and_push.return_value = True
        mock_github_client.return_value = mock_github_instance

        mock_vault_instance = MagicMock()
        mock_vault_instance.validate_vault_structure.return_value = True
        mock_vault_service.return_value = mock_vault_instance

        mock_builder_instance = MagicMock()
        mock_plan = MagicMock()
        mock_plan.strategy = "new_article"
        mock_builder_instance.analyze_vault.return_value = mock_plan

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.changes = []
        mock_result.summary = "Test"
        mock_result.agent_results = {}
        mock_builder_instance.execute_workflow.return_value = mock_result
        mock_graph_builder.return_value = mock_builder_instance

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/test/repo/pull/1"
        mock_github_instance.create_pull_request.return_value = mock_pr

        workflow_id = workflow.id

        with patch("src.tasks.workflow_tasks.settings") as mock_settings:
            mock_settings.WORKFLOW_CLONE_BASE_PATH = "/tmp/test"
            mock_settings.GITHUB_REPO_FULL_NAME = "test/repo"
            mock_settings.WORKFLOW_DEFAULT_BRANCH = "main"

            run_workflow_task(workflow_id)

        # Verify cleanup was called
        mock_rmtree.assert_called_once()

    @patch("src.tasks.workflow_tasks.get_db")
    def test_task_raises_error_for_nonexistent_workflow(self, mock_get_db, test_db):
        """Test that task raises error if workflow ID doesn't exist."""
        mock_get_db.return_value = iter([test_db])

        with pytest.raises(Exception) as exc_info:
            run_workflow_task(99999)

        assert "not found" in str(exc_info.value).lower()
