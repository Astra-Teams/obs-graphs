"""Pydantic schemas for the simplified workflow API."""

from typing import Dict, Optional

from pydantic import BaseModel, Field

from src.api.v1.models.workflow import WorkflowStatus


class CreateNewArticleRequest(BaseModel):
    """Request body for triggering the new-article workflow."""

    category: Optional[str] = Field(
        None,
        description="Optional category to prioritise. If omitted the first category is used.",
    )
    async_execution: bool = Field(
        False,
        description="Whether to execute the workflow asynchronously via Celery.",
    )
    vault_path: Optional[str] = Field(
        None,
        description="Optional path to the vault clone. Defaults to the configured workspace.",
    )


class CreateNewArticleResponse(BaseModel):
    """Response returned after triggering the workflow."""

    id: int
    status: WorkflowStatus
    message: str
    celery_task_id: Optional[str] = None
    pull_request_title: Optional[str] = None
    pull_request_body: Optional[str] = None
    pr_url: Optional[str] = None
    details: Optional[Dict] = None
