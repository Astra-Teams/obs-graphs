import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from src.api.v1.models.workflow import Workflow, WorkflowStatus
from src.api.v1.schemas import CreateNewArticleRequest
from src.db.database import get_db
from src.settings import get_settings
from src.tasks.celery_app import celery_app
from src.container import get_container

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(bind=True, name="run_workflow_task")
def run_workflow_task(self, workflow_id: int, request_data: dict) -> None:
    db: Session = next(get_db())
    workflow = None

    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(timezone.utc)
        workflow.celery_task_id = self.request.id
        db.commit()

        request = CreateNewArticleRequest(**request_data)
        graph_builder = get_container().get_graph_builder()
        result = graph_builder.run_new_article_workflow(request)

        if result.success:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.pr_url = result.pr_url
            workflow.workflow_metadata = {
                "request": request.model_dump(exclude_none=True),
                "result": result.metadata,
            }
        else:
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = result.error or "Workflow execution failed."

        workflow.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:  # pragma: no cover - defensive guard
        if workflow:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="cleanup_old_workflows")
def cleanup_old_workflows() -> None:
    clone_base_path = Path(settings.WORKFLOW_CLONE_BASE_PATH)

    if not clone_base_path.exists():
        return

    current_time = time.time()
    for temp_dir in clone_base_path.glob("workflow_*"):
        if temp_dir.is_dir():
            dir_age = current_time - temp_dir.stat().st_mtime
            if dir_age > settings.WORKFLOW_TEMP_DIR_CLEANUP_SECONDS:
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up old workflow directory: {temp_dir}")
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.error(f"Failed to clean up {temp_dir}: {exc}")
