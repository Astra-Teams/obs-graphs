"""Database integration tests for the Workflow model."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.db.models.workflow import Workflow, WorkflowStatus
from tests.db.conftest import (
    create_pending_workflow,
    create_running_workflow,
)


def test_create_pending_workflow_defaults(db_session: Session) -> None:
    """Persisting a pending workflow should populate defaults and timestamps."""
    workflow = create_pending_workflow(db_session)

    assert workflow.id is not None
    assert workflow.status is WorkflowStatus.PENDING
    assert workflow.created_at is not None
    assert workflow.started_at is None
    assert workflow.completed_at is None
    assert workflow.pr_url is None
    assert workflow.error_message is None
    assert (
        repr(workflow)
        == f"<Workflow(id={workflow.id}, status=PENDING, strategy=None, prompt=None)>"
    )


def test_workflow_transition_to_completed(db_session: Session) -> None:
    """Updating a running workflow to completed should persist audit details."""
    workflow = create_running_workflow(db_session, strategy="new_article")
    original_started_at = workflow.started_at

    completed_at = datetime.now(timezone.utc)
    workflow.status = WorkflowStatus.COMPLETED
    workflow.completed_at = completed_at
    workflow.pr_url = "https://github.com/test/repo/pull/99"
    workflow.workflow_metadata = {
        "agent_results": {"new_article": {"success": True, "changes_count": 1}},
        "total_changes": 1,
    }
    db_session.commit()
    db_session.refresh(workflow)

    assert workflow.status is WorkflowStatus.COMPLETED
    assert workflow.pr_url == "https://github.com/test/repo/pull/99"
    assert workflow.workflow_metadata["total_changes"] == 1
    assert workflow.workflow_metadata["agent_results"]["new_article"]["success"] is True
    assert workflow.started_at == original_started_at
    assert workflow.completed_at == completed_at.replace(tzinfo=None)


def test_failed_workflow_records_error_details(db_session: Session) -> None:
    """Failed workflows should persist error messages and timing metadata."""
    workflow = create_pending_workflow(db_session)

    started_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    completed_at = datetime.now(timezone.utc)
    workflow.status = WorkflowStatus.FAILED
    workflow.started_at = started_at
    workflow.completed_at = completed_at
    workflow.error_message = (
        "Workflow execution failed: GitHub API authentication error"
    )
    workflow.workflow_metadata = {
        "retry_count": 1,
        "last_attempt": completed_at.isoformat(),
    }
    db_session.commit()
    db_session.refresh(workflow)

    assert workflow.status is WorkflowStatus.FAILED
    assert workflow.error_message.startswith("Workflow execution failed")
    assert workflow.workflow_metadata["retry_count"] == 1
    assert workflow.started_at == started_at.replace(tzinfo=None)
    assert workflow.completed_at == completed_at.replace(tzinfo=None)


def test_query_workflows_by_status(db_session: Session) -> None:
    """Workflows should be filterable by status using SQLAlchemy queries."""
    create_pending_workflow(db_session)
    running = create_running_workflow(db_session)

    completed = Workflow(
        status=WorkflowStatus.COMPLETED, completed_at=datetime.now(timezone.utc)
    )
    db_session.add(completed)
    db_session.commit()

    running_workflows = (
        db_session.query(Workflow)
        .filter(Workflow.status == WorkflowStatus.RUNNING)
        .all()
    )
    assert {wf.id for wf in running_workflows} == {running.id}

    completed_workflows = (
        db_session.query(Workflow)
        .filter(Workflow.status == WorkflowStatus.COMPLETED)
        .all()
    )
    assert any(wf.id == completed.id for wf in completed_workflows)
