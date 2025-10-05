"""Celery tasks for executing Obsidian Vault workflows."""

import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from src.api.v1.models.workflow import Workflow, WorkflowStatus
from src.container import get_container
from src.db.database import get_db
from src.settings import get_settings
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()
container = get_container()


@celery_app.task(bind=True, name="run_workflow_task")
def run_workflow_task(self, workflow_id: int) -> None:
    """
    Execute a complete workflow: clone repo, run agents, commit, create PR.

    This task orchestrates the entire workflow lifecycle:
    1. Retrieve workflow from database
    2. Clone repository to temporary directory
    3. Analyze vault and execute agents via dependency container
    4. Apply changes to local clone via VaultService
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

        # 3. Create GraphBuilder and run workflow
        from src.api.v1.schemas import WorkflowRunRequest

        request = WorkflowRunRequest(strategy=workflow.strategy)
        graph_builder = container.get_graph_builder()
        result = graph_builder.run_workflow(request)

        # Update workflow based on result
        if result.success:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.pr_url = result.pr_url
            workflow.workflow_metadata = {
                "agent_results": result.agent_results,
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


@celery_app.task(name="cleanup_old_workflows")
def cleanup_old_workflows() -> None:
    """
    Periodic task to clean up old workflow temporary directories.

    This task should be scheduled to run periodically (e.g., daily) to
    ensure that any orphaned temporary directories are cleaned up.
    """
    clone_base_path = Path(settings.WORKFLOW_CLONE_BASE_PATH)

    if not clone_base_path.exists():
        return

    # Clean up any workflow_* directories older than configured seconds
    current_time = time.time()
    for temp_dir in clone_base_path.glob("workflow_*"):
        if temp_dir.is_dir():
            # Check if directory is older than configured time
            dir_age = current_time - temp_dir.stat().st_mtime
            if dir_age > settings.WORKFLOW_TEMP_DIR_CLEANUP_SECONDS:
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up old workflow directory: {temp_dir}")
                except Exception as e:
                    logger.error(f"Failed to clean up {temp_dir}: {e}")
