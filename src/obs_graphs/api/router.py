"""API endpoints for workflow management."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.obs_graphs.api.schemas import (
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from src.obs_graphs.config import obs_graphs_settings
from src.obs_graphs.db.database import get_db
from src.obs_graphs.db.models.workflow import Workflow, WorkflowStatus

router = APIRouter()


# Endpoints
@router.post("/workflows/run", response_model=WorkflowRunResponse, status_code=201)
async def run_workflow(
    request: WorkflowRunRequest,
    db: Session = Depends(get_db),
) -> WorkflowRunResponse:
    """
    Run a new workflow execution synchronously or asynchronously.

    Creates a new Workflow record in the database and executes the workflow.
    If async_execution is True, queues the workflow for background execution.
    If async_execution is False, executes synchronously.

    Args:
        request: Workflow run request with prompt, strategy, and execution mode
        db: Database session dependency

    Returns:
        WorkflowRunResponse with workflow ID, status, and message

    Raises:
        HTTPException: If workflow creation fails
    """
    try:
        # Create new workflow record with PENDING status
        selected_backend = (
            (request.backend or obs_graphs_settings.llm_backend).strip().lower()
        )

        prompts = request.prompts

        # Persist workflow with full prompt history
        workflow = Workflow(
            prompt=prompts,
            status=WorkflowStatus.PENDING,
            strategy=request.strategy,
        )
        workflow.workflow_metadata = {"backend": selected_backend}
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        if request.async_execution:
            # Asynchronous execution using Celery
            from src.obs_graphs.celery.tasks import run_workflow_task

            # Queue task only AFTER database commit is complete
            task = run_workflow_task.delay(workflow.id)

            # Update celery_task_id and commit again
            workflow.celery_task_id = task.id
            db.commit()

            return WorkflowRunResponse(
                id=workflow.id,
                status=workflow.status,
                celery_task_id=task.id,
                message="Workflow queued for asynchronous execution",
            )
        else:
            # Synchronous execution
            # Update to RUNNING
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now(timezone.utc)
            db.commit()

            # Set vault path for synchronous execution
            from src.obs_graphs.container import get_container

            container = get_container()
            # Find project root by searching for pyproject.toml
            current_path = Path(__file__).resolve().parent
            project_root = current_path
            while project_root.parent != project_root:  # Stop at filesystem root
                if (project_root / "pyproject.toml").exists():
                    break
                project_root = project_root.parent

            raw_path = Path(obs_graphs_settings.vault_submodule_path)
            vault_path = raw_path if raw_path.is_absolute() else project_root / raw_path
            container.set_vault_path(vault_path)

            # Create Graph and run workflow
            from src.obs_graphs.graphs.article_proposal.graph import (
                ArticleProposalGraph,
            )

            article_proposal_graph = ArticleProposalGraph()
            result = article_proposal_graph.run_workflow(request)

            # Update workflow based on result
            if result.success:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.branch_name = result.branch_name
                metadata = workflow.workflow_metadata or {}
                metadata.update(
                    {
                        "node_results": result.node_results,
                        "total_changes": len(result.changes),
                        "branch_name": result.branch_name,
                        "backend": selected_backend,
                    }
                )
                workflow.workflow_metadata = metadata
            else:
                workflow.status = WorkflowStatus.FAILED
                workflow.error_message = result.summary
                # Ensure backend is recorded in metadata on failure as well
                metadata = workflow.workflow_metadata or {}
                metadata.setdefault("backend", selected_backend)
                workflow.workflow_metadata = metadata

            workflow.completed_at = datetime.now(timezone.utc)
            db.commit()

            return WorkflowRunResponse(
                id=workflow.id,
                status=workflow.status,
                celery_task_id=None,  # No Celery task for synchronous execution
                message=(
                    result.summary
                    if result.success
                    else f"Workflow failed: {result.summary}"
                ),
            )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run workflow: {str(e)}",
        )


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
) -> WorkflowResponse:
    """
    Get details of a specific workflow.

    Returns the workflow status, branch name if completed, error message if failed,
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
        status=workflow.status,
        strategy=workflow.strategy,
        started_at=workflow.started_at.isoformat() if workflow.started_at else None,
        completed_at=(
            workflow.completed_at.isoformat() if workflow.completed_at else None
        ),
        branch_name=workflow.branch_name,
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
        le=obs_graphs_settings.api_max_page_size,
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
        limit: Maximum number of results (default 10)
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
            status=w.status,
            strategy=w.strategy,
            started_at=w.started_at.isoformat() if w.started_at else None,
            completed_at=w.completed_at.isoformat() if w.completed_at else None,
            branch_name=w.branch_name,
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
