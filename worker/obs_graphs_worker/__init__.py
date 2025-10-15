"""Celery worker package for obs-graphs."""

from .app import celery_app

__all__ = ["celery_app"]
