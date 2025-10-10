"""Celery tasks for executing Obsidian Vault workflows."""

import logging
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from src.obs_graphs.celery.app import celery_app
from src.obs_graphs.db.database import get_db
from src.obs_graphs.db.models.workflow import Workflow, WorkflowStatus
from src.obs_graphs.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_TEMP_BASE_PATH = Path(tempfile.gettempdir()) / "obs_graphs" / "workflows"


def _resolve_submodule_path() -> Path:
    """Resolve the configured vault submodule path to an absolute path."""
    raw_path = Path(settings.vault_submodule_path)
    source = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
    return source


def _prepare_workflow_directory(workflow_id: int) -> Path:
    """Copy the vault submodule into an isolated temporary directory."""
    WORKFLOW_TEMP_BASE_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    temp_dir = WORKFLOW_TEMP_BASE_PATH / f"workflow_{workflow_id}_{timestamp}"

    source = _resolve_submodule_path()
    if not source.exists():
        raise FileNotFoundError(
            f"Configured vault submodule path does not exist: {source}"
        )

    shutil.copytree(source, temp_dir)
    return temp_dir


@celery_app.task(bind=True, name="run_workflow_task")
def run_workflow_task(self, workflow_id: int) -> None:
    """
    Execute a complete workflow: clone repo, run agents, commit, create PR.

    This task orchestrates the entire workflow lifecycle:
    1. Retrieve workflow from database
    2. Copy vault submodule to a temporary working directory
    3. Analyze vault and execute agents via dependency container
    4. Apply changes through the VaultService/GitHub API
    5. Commit and push changes via GithubClient
    6. Create pull request on GitHub
    7. Update workflow status and store results
    8. Clean up temporary directory

    Args:
        workflow_id: Database ID of the workflow to execute

    Raises:
        Exception: Any error during workflow execution (caught and stored in DB)
    """
    # Get database session
    db: Session = next(get_db())
    workflow = None
    temp_vault_dir: Path | None = None

    try:
        # 1. Retrieve workflow from database
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # 2. Update status to RUNNING
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(timezone.utc)
        workflow.celery_task_id = self.request.id
        db.commit()

        # 3. Prepare local workflow directory from vault submodule
        temp_vault_dir = _prepare_workflow_directory(workflow_id)

        # Set the path in the container
        from src.obs_graphs.container import get_container

        container = get_container()
        container.set_vault_path(temp_vault_dir)

        # 4. Create ArticleProposalGraph and run workflow
        from src.obs_graphs.api.schemas import WorkflowRunRequest

        request = WorkflowRunRequest(
            prompt=workflow.prompt or "",
            strategy=workflow.strategy,
        )
        graph_builder = container.get_graph_builder()
        result = graph_builder.run_workflow(request)

        # Update workflow based on result
        if result.success:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.pr_url = result.pr_url
            workflow.workflow_metadata = {
                "node_results": result.node_results,
                "total_changes": len(result.changes),
                "branch_name": result.branch_name,
            }
        else:
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = result.summary

        workflow.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        # Update workflow to FAILED
        if workflow:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.error_message = str(e)
            db.commit()

        # Re-raise exception for Celery to handle
        raise

    finally:
        # Close database session
        db.close()

        # Remove temporary workflow directory
        if temp_vault_dir and temp_vault_dir.exists():
            shutil.rmtree(temp_vault_dir, ignore_errors=True)


@celery_app.task(name="cleanup_old_workflows")
def cleanup_old_workflows() -> None:
    """
    Periodic task to clean up old workflow temporary directories.

    This task should be scheduled to run periodically (e.g., daily) to
    ensure that any orphaned temporary directories are cleaned up.
    """
    clone_base_path = WORKFLOW_TEMP_BASE_PATH

    if not clone_base_path.exists():
        return

    # Clean up any workflow_* directories older than configured seconds
    current_time = time.time()
    for temp_dir in clone_base_path.glob("workflow_*"):
        if temp_dir.is_dir():
            # Check if directory is older than configured time
            dir_age = current_time - temp_dir.stat().st_mtime
            if dir_age > settings.workflow_temp_dir_cleanup_seconds:
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up old workflow directory: {temp_dir}")
                except Exception as e:
                    logger.error(f"Failed to clean up {temp_dir}: {e}")
