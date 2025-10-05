from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.v1.graph import GraphBuilder
from src.api.v1.models.workflow import Workflow, WorkflowStatus
from src.api.v1.schemas import CreateNewArticleRequest, CreateNewArticleResponse
from src.api.v1.tasks.workflow_tasks import run_workflow_task
from src.db.database import get_db

router = APIRouter()


@router.post(
    "/workflows/create-new-article",
    response_model=CreateNewArticleResponse,
    status_code=200,
)
async def create_new_article_workflow(
    request: CreateNewArticleRequest, db: Session = Depends(get_db)
) -> CreateNewArticleResponse:
    try:
        workflow = Workflow(status=WorkflowStatus.PENDING)
        workflow.workflow_metadata = {
            "request": request.model_dump(exclude_none=True)
        }
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        if request.async_execution:
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now(timezone.utc)
            db.commit()

            task = run_workflow_task.delay(workflow.id, request.model_dump())
            workflow.celery_task_id = task.id
            db.commit()

            return CreateNewArticleResponse(
                id=workflow.id,
                status=workflow.status,
                message="Workflow queued for asynchronous execution",
                celery_task_id=task.id,
            )

        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(timezone.utc)
        db.commit()

        graph_builder = GraphBuilder()
        result = graph_builder.run_new_article_workflow(request)

        if result.success:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.pr_url = result.pr_url
            workflow.workflow_metadata = {
                "request": request.model_dump(exclude_none=True),
                "result": result.metadata,
            }
            message = "Workflow completed successfully."
        else:
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = result.error or "Workflow execution failed."
            message = workflow.error_message

        workflow.completed_at = datetime.now(timezone.utc)
        db.commit()

        return CreateNewArticleResponse(
            id=workflow.id,
            status=workflow.status,
            message=message,
            pull_request_title=result.pull_request_title,
            pull_request_body=result.pull_request_body,
            pr_url=result.pr_url,
            details=result.metadata if result.success else None,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        db.rollback()
        raise HTTPException(500, detail=f"Failed to trigger workflow: {exc}") from exc
