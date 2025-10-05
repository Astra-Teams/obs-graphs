"""Pydantic models for API request and response schemas."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.db.models.workflow import WorkflowStatus
from src.state import WorkflowStrategy


class WorkflowRunRequest(BaseModel):
    """Request body for running a new workflow."""

    strategy: Optional[WorkflowStrategy] = Field(
        None,
        description="Optional strategy to force specific workflow type",
    )


class WorkflowResponse(BaseModel):
    """Response model for workflow information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: WorkflowStatus
    strategy: Optional[WorkflowStrategy]
    started_at: Optional[str]
    completed_at: Optional[str]
    pr_url: Optional[str]
    error_message: Optional[str]
    celery_task_id: Optional[str]
    created_at: str


class WorkflowRunResponse(BaseModel):
    """Response for workflow run endpoint."""

    id: int
    status: WorkflowStatus
    celery_task_id: str
    message: str


class WorkflowListResponse(BaseModel):
    """Response for workflow list endpoint."""

    workflows: List[WorkflowResponse]
    total: int
    limit: int
    offset: int
