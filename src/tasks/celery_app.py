"""Celery application configuration for background task processing."""

from celery import Celery

from src.config.settings import get_settings

settings = get_settings()

# Initialize Celery app with Redis broker
celery_app = Celery(
    "obsidian_agents",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks.workflow_tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task time limits (10 minutes max per task)
    task_time_limit=600,
    task_soft_time_limit=540,
    # Task routing
    task_routes={
        "src.tasks.workflow_tasks.run_workflow_task": {"queue": "workflows"},
    },
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["src.tasks"])
