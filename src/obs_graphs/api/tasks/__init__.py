"""API Celery tasks."""

from src.obs_graphs.api.tasks.workflow_tasks import run_workflow_task

__all__ = ["run_workflow_task"]
