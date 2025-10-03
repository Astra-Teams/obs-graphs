"""API endpoints for workflow management."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models.workflow import Workflow, WorkflowStatus
from src.tasks.workflow_tasks import run_workflow_task

router = APIRouter()


# Request/Response Models
class WorkflowRunRequest(BaseModel):
    """Request body for running a new workflow."""

    strategy: Optional[str] = Field(
        None,
        description="Optional strategy to force specific workflow type (e.g., 'new_article', 'improvement')",
        max_length=100,
    )


class WorkflowResponse(BaseModel):
    """Response model for workflow information."""

    id: int
    status: str
    strategy: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    pr_url: Optional[str]
    error_message: Optional[str]
    celery_task_id: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class WorkflowRunResponse(BaseModel):
    """Response for workflow run endpoint."""

    id: int
    status: str
    celery_task_id: str
    message: str


class WorkflowListResponse(BaseModel):
    """Response for workflow list endpoint."""

    workflows: List[WorkflowResponse]
    total: int
    limit: int
    offset: int


# Endpoints
@router.post("/workflows/run", response_model=WorkflowRunResponse, status_code=201)
async def run_workflow(
    request: WorkflowRunRequest = WorkflowRunRequest(),
    db: Session = Depends(get_db),
) -> WorkflowRunResponse:
    """
    Trigger a new workflow execution.

    Creates a new Workflow record in the database with status=PENDING,
    dispatches the run_workflow_task to Celery, and returns immediately
    with the workflow ID and Celery task ID.

    Args:
        request: Optional workflow run request with strategy parameter
        db: Database session dependency

    Returns:
        WorkflowRunResponse with workflow ID, status, and task ID

    Raises:
        HTTPException: If workflow creation or task dispatch fails
    """
    try:
        # Create new workflow record with PENDING status
        workflow = Workflow(
            status=WorkflowStatus.PENDING,
            strategy=request.strategy,
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        # Dispatch Celery task
        task = run_workflow_task.delay(workflow.id)

        # Store Celery task ID in workflow record
        workflow.celery_task_id = task.id
        db.commit()

        return WorkflowRunResponse(
            id=workflow.id,
            status=workflow.status.value,
            celery_task_id=task.id,
            message=f"Workflow {workflow.id} has been queued for execution",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow: {str(e)}",
        )


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
) -> WorkflowResponse:
    """
    Get details of a specific workflow.

    Returns the workflow status, PR URL if completed, error message if failed,
    and other workflow metadata.

    Args:
        workflow_id: ID of the workflow to retrieve
        db: Database session dependency

    Returns:
        WorkflowResponse with workflow details

    Raises:
        HTTPException: 404 if workflow not found
    """
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse(
        id=workflow.id,
        status=workflow.status.value,
        strategy=workflow.strategy,
        started_at=workflow.started_at.isoformat() if workflow.started_at else None,
        completed_at=(
            workflow.completed_at.isoformat() if workflow.completed_at else None
        ),
        pr_url=workflow.pr_url,
        error_message=workflow.error_message,
        celery_task_id=workflow.celery_task_id,
        created_at=workflow.created_at.isoformat(),
    )


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[str] = Query(
        None,
        description="Filter by workflow status (PENDING, RUNNING, COMPLETED, FAILED)",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of workflows to return",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of workflows to skip",
    ),
    db: Session = Depends(get_db),
) -> WorkflowListResponse:
    """
    List workflows with pagination and filtering.

    Returns a paginated list of workflows, optionally filtered by status.

    Args:
        status: Optional status filter (pending, running, completed, failed)
        limit: Maximum number of results (1-100, default 10)
        offset: Number of results to skip (default 0)
        db: Database session dependency

    Returns:
        WorkflowListResponse with list of workflows and pagination info

    Raises:
        HTTPException: 400 if invalid status value provided
    """
    # Build query
    query = db.query(Workflow)

    # Apply status filter if provided
    if status:
        try:
            status_enum = WorkflowStatus(status)
            query = query.filter(Workflow.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Must be one of: PENDING, RUNNING, COMPLETED, FAILED",
            )

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    workflows = (
        query.order_by(Workflow.created_at.desc()).offset(offset).limit(limit).all()
    )

    # Convert to response models
    workflow_responses = [
        WorkflowResponse(
            id=w.id,
            status=w.status.value,
            strategy=w.strategy,
            started_at=w.started_at.isoformat() if w.started_at else None,
            completed_at=w.completed_at.isoformat() if w.completed_at else None,
            pr_url=w.pr_url,
            error_message=w.error_message,
            celery_task_id=w.celery_task_id,
            created_at=w.created_at.isoformat(),
        )
        for w in workflows
    ]

    return WorkflowListResponse(
        workflows=workflow_responses,
        total=total,
        limit=limit,
        offset=offset,
    )
