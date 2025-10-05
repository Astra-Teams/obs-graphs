"""Factory functions for creating test workflow records."""

from datetime import datetime, timedelta, timezone

from src.api.v1.models.workflow import Workflow, WorkflowStatus


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
        workflow_metadata=kwargs.get("workflow_metadata", {"agents_executed": []}),
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
                "agent_results": {
                    "new_article": {
                        "success": True,
                        "message": "Created 2 new articles",
                        "changes_count": 2,
                    },
                    "quality_audit": {
                        "success": True,
                        "message": "All checks passed",
                        "changes_count": 0,
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
