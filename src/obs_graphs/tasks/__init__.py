"""Celery tasks for background workflow execution."""

from src.obs_graphs.tasks.celery_app import celery_app

__all__ = ["celery_app"]
