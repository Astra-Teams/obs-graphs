"""Pydantic models for API request and response schemas."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.obs_graphs.db.models.workflow import WorkflowStatus
from src.obs_graphs.graphs.article_proposal.state import WorkflowStrategy


class WorkflowRunRequest(BaseModel):
    """Request body for running a new workflow."""

    prompt: str = Field(
        ...,
        description="Research prompt or keywords to investigate. Required for initiating research workflows.",
    )
    strategy: Optional[WorkflowStrategy] = Field(
        None,
        description="Optional strategy to force specific workflow type",
    )
    async_execution: bool = Field(
        False,
        description="Whether to execute workflow asynchronously using Celery",
    )

    @field_validator("prompt", mode="after")
    @classmethod
    def validate_prompt_not_whitespace(cls, v: str) -> str:
        """Validate that prompt contains non-whitespace content."""
        if not v or not v.strip():
            raise ValueError("Prompt is required and cannot be empty")
        return v.strip()


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
    celery_task_id: Optional[str]
    message: str


class WorkflowListResponse(BaseModel):
    """Response for workflow list endpoint."""

    workflows: List[WorkflowResponse]
    total: int
    limit: int
    offset: int
