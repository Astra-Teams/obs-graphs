"""API endpoints for workflow management."""

from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from obs_gtwy_sdk import GatewayClientProtocol
from olm_d_rch_sdk import ResearchClientProtocol
from sqlalchemy.orm import Session

from src.obs_graphs import dependencies
from src.obs_graphs.api.schemas import (
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from src.obs_graphs.config import obs_graphs_settings
from src.obs_graphs.db.models.workflow import Workflow, WorkflowStatus
from src.obs_graphs.protocols import StlConnClientProtocol, VaultServiceProtocol

router = APIRouter()


# Endpoints
@router.post(
    "/workflows/{workflow_type}/run",
    response_model=WorkflowRunResponse,
    status_code=201,
)
async def run_workflow(
    workflow_type: str,
    request: WorkflowRunRequest,
    db: Session = Depends(dependencies.get_db_session),
    vault_service: VaultServiceProtocol = Depends(dependencies.get_vault_service),
    llm_client_provider: Callable[[], StlConnClientProtocol] = Depends(
        dependencies.get_llm_client_provider
    ),
    gateway_client: GatewayClientProtocol = Depends(dependencies.get_gateway_client),
    research_client: ResearchClientProtocol = Depends(dependencies.get_research_client),
) -> WorkflowRunResponse:
    """
    Run a workflow of the specified type.

    Creates a new Workflow record in the database and executes the workflow.
    If async_execution is True, queues the workflow for background execution.
    If async_execution is False, executes synchronously.

    Args:
        workflow_type: Type of workflow to run (e.g., 'article-proposal')
        request: Workflow run request with prompts and configuration
        db: Database session dependency

    Returns:
        WorkflowRunResponse with workflow ID, status, and message

    Raises:
        HTTPException: If workflow creation fails or unknown workflow type

    Supported workflow types:
        - article-proposal: Research topic proposal and article creation
    """
    try:
        # Validate workflow type and create graph builder with dependencies
        from src.obs_graphs.graphs.factory import get_graph_builder

        try:
            graph_builder = get_graph_builder(
                workflow_type=workflow_type,
                vault_service=vault_service,
                llm_client_provider=llm_client_provider,
                gateway_client=gateway_client,
                research_client=research_client,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Create new workflow record with PENDING status
        prompts = request.prompts

        # Persist workflow with full prompt history
        workflow = Workflow(
            workflow_type=workflow_type,
            prompt=prompts,
            status=WorkflowStatus.PENDING,
            strategy=request.strategy,
        )
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

            # Run workflow with injected dependencies (vault_service already configured)
            result = graph_builder.run_workflow(request)

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
                    }
                )
                workflow.workflow_metadata = metadata
            else:
                workflow.status = WorkflowStatus.FAILED
                workflow.error_message = result.summary
                # Ensure metadata is recorded on failure as well
                workflow.workflow_metadata = workflow.workflow_metadata

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
    db: Session = Depends(dependencies.get_db_session),
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
    db: Session = Depends(dependencies.get_db_session),
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
