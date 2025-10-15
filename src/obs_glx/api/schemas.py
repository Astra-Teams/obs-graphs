"""Pydantic models for API request and response schemas."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.obs_glx.db.models.workflow import WorkflowStatus
from src.obs_glx.graphs.article_proposal.state import WorkflowStrategy


class WorkflowRunRequest(BaseModel):
    """Request body for running a new workflow."""

    prompts: List[str] = Field(
        ...,
        description=(
            "Ordered list of prompts or workflow instructions. The first prompt "
            "represents the entry point and subsequent prompts provide follow-up "
            "instructions."
        ),
    )
    strategy: Optional[WorkflowStrategy] = Field(
        None,
        description="Optional strategy to force specific workflow type",
    )
    async_execution: bool = Field(
        False,
        description="Whether to execute workflow asynchronously using Celery",
    )

    @field_validator("prompts", mode="after")
    @classmethod
    def validate_prompts(cls, prompts: List[str]) -> List[str]:
        """Ensure prompts are provided and contain non-empty strings."""

        if not prompts:
            raise ValueError("At least one prompt is required")

        cleaned: List[str] = []
        for index, prompt in enumerate(prompts):
            stripped = prompt.strip()
            if not stripped:
                raise ValueError(
                    f"Prompts cannot contain empty strings; index {index} is empty."
                )
            cleaned.append(stripped)

        return cleaned

    @property
    def primary_prompt(self) -> str:
        """Return the first prompt, which acts as the entry point for workflows."""

        return self.prompts[0]


class WorkflowResponse(BaseModel):
    """Response model for workflow information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: WorkflowStatus
    strategy: Optional[WorkflowStrategy]
    started_at: Optional[str]
    completed_at: Optional[str]
    branch_name: Optional[str]
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
