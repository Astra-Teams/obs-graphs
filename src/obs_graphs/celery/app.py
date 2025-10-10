"""Celery application configuration for background task processing."""

import os

from celery import Celery

# Initialize Celery app with environment variables directly
# This avoids importing settings during module load, which allows tests to mock
celery_app = Celery(
    "obsidian_agents",
    broker=os.getenv("OBS_GRAPHS_CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("OBS_GRAPHS_CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=["src.obs_graphs.celery.tasks"],
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
        "src.obs_graphs.celery.tasks.run_workflow_task": {"queue": "workflows"},
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
celery_app.autodiscover_tasks(["src.obs_graphs.celery.tasks"])
