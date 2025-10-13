"""Database test specific fixtures and factory functions."""

from datetime import datetime, timedelta, timezone

import pytest

from src.obs_graphs.db.models.workflow import Workflow, WorkflowStatus


@pytest.fixture(autouse=True)
def set_db_test_env(monkeypatch):
    """Setup environment variables for database tests."""
    # monkeypatch.setenv("USE_SQLITE", "false")  # Commented out to allow db switching tests
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK_REDIS", "true")
    monkeypatch.setenv("USE_MOCK_OLLAMA_DEEP_RESEARCHER", "true")
    monkeypatch.setenv("USE_MOCK_OBS_GTWY", "true")
    monkeypatch.setenv("OBS_GRAPHS_OLLAMA_MODEL", "tinyllama:1.1b")
    monkeypatch.setenv("RESEARCH_API_OLLAMA_MODEL", "tinyllama:1.1b")


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
    prompt_value = kwargs.get("prompt", ["Test research prompt"])
    if isinstance(prompt_value, str):
        prompt_value = [prompt_value]

    workflow = Workflow(
        prompt=prompt_value,
        status=WorkflowStatus.PENDING,
        strategy=kwargs.get("strategy", None),
        started_at=None,
        completed_at=None,
        branch_name=None,
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
    prompt_value = kwargs.get("prompt", ["Test research prompt"])
    if isinstance(prompt_value, str):
        prompt_value = [prompt_value]

    workflow = Workflow(
        prompt=prompt_value,
        status=WorkflowStatus.RUNNING,
        strategy=kwargs.get("strategy", "new_article"),
        started_at=kwargs.get("started_at", datetime.now(timezone.utc)),
        completed_at=None,
        branch_name=None,
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
    db_session, with_branch: bool = True, **kwargs
) -> Workflow:
    """
    Create a workflow in COMPLETED state.

    Args:
        db_session: SQLAlchemy database session
        with_branch: Whether to include a branch name
        **kwargs: Optional fields to override defaults

    Returns:
        Workflow instance in COMPLETED state
    """
    branch_name = None
    if with_branch:
        branch_name = kwargs.get("branch_name", "draft/sample-draft")

    created_at = kwargs.get(
        "created_at", datetime.now(timezone.utc) - timedelta(hours=1)
    )
    started_at = kwargs.get("started_at", created_at + timedelta(seconds=30))
    completed_at = kwargs.get("completed_at", started_at + timedelta(minutes=10))

    prompt_value = kwargs.get("prompt", ["Test research prompt"])
    if isinstance(prompt_value, str):
        prompt_value = [prompt_value]

    workflow = Workflow(
        prompt=prompt_value,
        status=WorkflowStatus.COMPLETED,
        strategy=kwargs.get("strategy", "new_article"),
        started_at=started_at,
        completed_at=completed_at,
        branch_name=branch_name,
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

    prompt_value = kwargs.get("prompt", ["Test research prompt"])
    if isinstance(prompt_value, str):
        prompt_value = [prompt_value]

    workflow = Workflow(
        prompt=prompt_value,
        status=WorkflowStatus.FAILED,
        strategy=kwargs.get("strategy", "improvement"),
        started_at=started_at,
        completed_at=completed_at,
        branch_name=None,
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
        branch_name=kwargs.get("branch_name", None),
        error_message=kwargs.get("error_message", None),
        celery_task_id=kwargs.get("celery_task_id", "test-task-custom-999"),
        workflow_metadata=metadata,
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
    )

    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    return workflow
