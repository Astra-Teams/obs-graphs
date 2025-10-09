"""Database test specific fixtures and factory functions."""

from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.v1.models.workflow import Workflow, WorkflowStatus
from src.db.database import create_db_session
from src.main import app


@pytest.fixture(scope="module")
def test_db_settings(default_settings):
    """Provide settings for DB tests."""

    updated_settings = default_settings.model_copy(
        update={
            "use_sqlite": False,
            "db_settings": default_settings.db_settings.model_copy(
                update={"db_host": "localhost", "db_port": 5433, "db_name": "test_db"}
            ),
        }
    )

    from src import settings as settings_module

    original_settings = settings_module.settings
    settings_module.settings = updated_settings

    try:
        yield updated_settings
    finally:
        settings_module.settings = original_settings


@pytest.fixture(scope="module")
def test_engine(test_db_settings):
    return create_engine(test_db_settings.db_settings.database_url)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Provides a transaction-scoped session for each test function.

    Tests run within transactions and are rolled back on completion,
    ensuring DB state independence between tests.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = SessionLocal()

    # Override FastAPI app's DI (get_db) with this test session
    app.dependency_overrides[create_db_session] = lambda: db

    try:
        yield db
    finally:
        db.rollback()  # Rollback all changes
        db.close()
        app.dependency_overrides.pop(create_db_session, None)


# Existing factory functions...


def create_pending_workflow(db_session, **kwargs) -> Workflow:
    """
    Create a workflow in PENDING state.

    Args:
        db_session: SQLAlchemy database session
        **kwargs: Optional fields to override defaults

    Returns:
        Workflow instance in PENDING state
    """
    workflow = Workflow(
        status=WorkflowStatus.PENDING,
        strategy=kwargs.get("strategy", None),
        started_at=None,
        completed_at=None,
        pr_url=None,
        error_message=None,
        celery_task_id=kwargs.get("celery_task_id", None),
        workflow_metadata=kwargs.get("workflow_metadata", None),
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
    )

    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    return workflow


def create_running_workflow(db_session, **kwargs) -> Workflow:
    """
    Create a workflow in RUNNING state.

    Args:
        db_session: SQLAlchemy database session
        **kwargs: Optional fields to override defaults

    Returns:
        Workflow instance in RUNNING state
    """
    workflow = Workflow(
        status=WorkflowStatus.RUNNING,
        strategy=kwargs.get("strategy", "new_article"),
        started_at=kwargs.get("started_at", datetime.now(timezone.utc)),
        completed_at=None,
        pr_url=None,
        error_message=None,
        celery_task_id=kwargs.get("celery_task_id", "test-task-id-123"),
        workflow_metadata=kwargs.get("workflow_metadata", {"nodes_executed": []}),
        created_at=kwargs.get(
            "created_at", datetime.now(timezone.utc) - timedelta(minutes=5)
        ),
    )

    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    return workflow


def create_completed_workflow(
    db_session, with_pr_url: bool = True, **kwargs
) -> Workflow:
    """
    Create a workflow in COMPLETED state.

    Args:
        db_session: SQLAlchemy database session
        with_pr_url: Whether to include a PR URL
        **kwargs: Optional fields to override defaults

    Returns:
        Workflow instance in COMPLETED state
    """
    pr_url = None
    if with_pr_url:
        pr_url = kwargs.get("pr_url", "https://github.com/test-user/test-vault/pull/42")

    created_at = kwargs.get(
        "created_at", datetime.now(timezone.utc) - timedelta(hours=1)
    )
    started_at = kwargs.get("started_at", created_at + timedelta(seconds=30))
    completed_at = kwargs.get("completed_at", started_at + timedelta(minutes=10))

    workflow = Workflow(
        status=WorkflowStatus.COMPLETED,
        strategy=kwargs.get("strategy", "new_article"),
        started_at=started_at,
        completed_at=completed_at,
        pr_url=pr_url,
        error_message=None,
        celery_task_id=kwargs.get("celery_task_id", "test-task-completed-456"),
        workflow_metadata=kwargs.get(
            "workflow_metadata",
            {
                "node_results": {
                    "new_article": {
                        "success": True,
                        "message": "Created 2 new articles",
                        "changes_count": 2,
                    },
                },
                "total_changes": 2,
                "branch_name": "obsidian-agents/1-new_article",
            },
        ),
        created_at=created_at,
    )

    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    return workflow


def create_failed_workflow(
    db_session, with_error_message: bool = True, **kwargs
) -> Workflow:
    """
    Create a workflow in FAILED state.

    Args:
        db_session: SQLAlchemy database session
        with_error_message: Whether to include an error message
        **kwargs: Optional fields to override defaults

    Returns:
        Workflow instance in FAILED state
    """
    error_message = None
    if with_error_message:
        error_message = kwargs.get(
            "error_message",
            "Workflow execution failed: GitHub API authentication error",
        )

    created_at = kwargs.get(
        "created_at", datetime.now(timezone.utc) - timedelta(hours=2)
    )
    started_at = kwargs.get("started_at", created_at + timedelta(seconds=30))
    completed_at = kwargs.get("completed_at", started_at + timedelta(minutes=2))

    workflow = Workflow(
        status=WorkflowStatus.FAILED,
        strategy=kwargs.get("strategy", "improvement"),
        started_at=started_at,
        completed_at=completed_at,
        pr_url=None,
        error_message=error_message,
        celery_task_id=kwargs.get("celery_task_id", "test-task-failed-789"),
        workflow_metadata=kwargs.get(
            "workflow_metadata",
            {"error_details": "API rate limit exceeded", "retry_count": 0},
        ),
        created_at=created_at,
    )

    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    return workflow


def create_workflow_with_custom_metadata(
    db_session, status: WorkflowStatus, metadata: dict, **kwargs
) -> Workflow:
    """
    Create a workflow with custom metadata.

    Args:
        db_session: SQLAlchemy database session
        status: Workflow status
        metadata: Custom metadata dictionary
        **kwargs: Optional fields to override defaults

    Returns:
        Workflow instance with custom metadata
    """
    workflow = Workflow(
        status=status,
        strategy=kwargs.get("strategy", "custom"),
        started_at=kwargs.get("started_at", datetime.now(timezone.utc)),
        completed_at=kwargs.get("completed_at", None),
        pr_url=kwargs.get("pr_url", None),
        error_message=kwargs.get("error_message", None),
        celery_task_id=kwargs.get("celery_task_id", "test-task-custom-999"),
        workflow_metadata=metadata,
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
    )

    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    return workflow
